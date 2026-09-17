"""
AudioShield Downstream Voice-Cloning Evaluation Module
======================================================
Reproducible downstream embedding-conditioned TTS experiment used as a
surrogate zero-shot voice-cloning proxy.

Cloning model:
  - microsoft/speecht5_tts (TTS) + microsoft/speecht5_hifigan (vocoder)
  - transformers 4.57.6, torch 2.8.0 / torchaudio 2.8.0
  - HF revision (tts): 30fcde30f19b87502b8435427b5f5068e401d5f6 (refs/main)
  - License: Apache 2.0 (model card: microsoft/speecht5_tts)
  - Conditioning: 512-dim speaker embedding. This experiment derives the
    conditioning vector from SpeechBrain ECAPA-TDNN (192-dim, L2-normalized)
    zero-padded to 512-dim. This is NON-STANDARD for SpeechT5 (which is
    normally conditioned on its own x-vector checkpoint) and is documented
    as a limitation: results measure sensitivity of embedding-conditioned
    synthesis to AudioShield perturbation, NOT certified resistance against
    dedicated zero-shot cloners (XTTS-v2, Bark, VALL-E X, OpenVoice).
  - Inference: processor(text) -> model.generate_speech(input_ids,
    speaker_embedding, vocoder) at 16 kHz, CPU, eval mode, torch.no_grad().
  - Weights are downloaded from HuggingFace Hub at runtime and are NOT
    committed to Git.

Conditions (identical text, inference settings, synthesis params):
  A. original_ref   : original LibriSpeech reference -> clone
  B. protected_ref  : AudioShield-protected reference -> clone
  C. unrelated_ref  : different-speaker reference -> clone (control)

Evaluation per clone (existing project evaluators only):
  - Speaker similarity: SpeechBrain ECAPA-TDNN
    (speechbrain/spkrec-ecapa-voxceleb, speechbrain 1.1.1) cosine similarity
    between source-speaker reference embedding and clone embedding.
  - Intelligibility: local ASR if available (openai/whisper-tiny via
    transformers, else WER=null with reason recorded). WER vs. known prompt.
  - Audio quality: duration, clipping count (|x|>0.999), NaN/Inf count.
    STOI and source-vs-clone SNR/SI-SDR are deliberately NOT reported:
    source and clone are different waveforms (different linguistic content
    and synthesis pipeline), so waveform-aligned ratios are not meaningful.

Outputs:
  - evaluation/results/voice_cloning_results.json
  - evaluation/results/voice_cloning_results.csv
  - evaluation/results/voice_cloning_summary.md
  - evaluation/results/voice_cloning_manifest.json (deterministic manifest)
  - evaluation/results/cloned_audio/*.wav
"""

import argparse
import csv
import dataclasses
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf
import torch
import torch.nn.functional as F

# Ensure repo root and worker are in sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
sys.path.insert(0, str(ROOT))

from tasks.protect import load_audio  # noqa: E402
from evaluation.metrics import extract_speaker_embedding  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("audioshield.voice_cloning")

# ---------------------------------------------------------------------------
# Model documentation constants (reproducibility)
# ---------------------------------------------------------------------------
TTS_MODEL_ID = "microsoft/speecht5_tts"
VOCODER_MODEL_ID = "microsoft/speecht5_hifigan"
TTS_REVISION = "30fcde30f19b87502b8435427b5f5068e401d5f6"
MODEL_LICENSE = "Apache 2.0"
SPEAKER_ENCODER_ID = "speechbrain/spkrec-ecapa-voxceleb"
ASR_MODEL_ID = "openai/whisper-tiny"

EVAL_PROMPTS = [
    "The quick brown fox jumps over the lazy dog.",
    "AudioShield provides adversarial voice protection for human speech.",
    "Speech synthesis models generate natural sounding voice profiles.",
]


def compute_wer(reference_text: str, hypothesis_text: str) -> float:
    """Compute Word Error Rate (WER) between reference and hypothesis texts."""
    ref_words = reference_text.lower().strip().split()
    hyp_words = hypothesis_text.lower().strip().split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    if not hyp_words:
        return 1.0

    d = np.zeros((len(ref_words) + 1, len(hyp_words) + 1), dtype=np.int32)
    for i in range(len(ref_words) + 1):
        d[i, 0] = i
    for j in range(len(hyp_words) + 1):
        d[0, j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                d[i, j] = d[i - 1, j - 1]
            else:
                substitution = d[i - 1, j - 1] + 1
                insertion = d[i, j - 1] + 1
                deletion = d[i - 1, j] + 1
                d[i, j] = min(substitution, insertion, deletion)

    return float(d[len(ref_words), len(hyp_words)] / len(ref_words))


def _stats(values: List[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"n": 0, "mean": None, "median": None, "std": None,
                "min": None, "max": None}
    arr = np.array(values, dtype=np.float64)
    return {
        "n": len(values),
        "mean": round(float(np.mean(arr)), 4),
        "median": round(float(np.median(arr)), 4),
        "std": round(float(np.std(arr)), 4),
        "min": round(float(np.min(arr)), 4),
        "max": round(float(np.max(arr)), 4),
    }


class VoiceCloningPipeline:
    def __init__(self, device: str = "cpu"):
        self.device = device
        self.asr_available = False
        self.asr_reason = ""
        self._load_models()

    def _load_models(self):
        logger.info("Loading SpeechT5 TTS Processor, Model, and HiFiGAN Vocoder...")
        from transformers import (SpeechT5ForTextToSpeech, SpeechT5HifiGan,
                                  SpeechT5Processor)

        try:
            self.tts_processor = SpeechT5Processor.from_pretrained(TTS_MODEL_ID)
            self.tts_model = SpeechT5ForTextToSpeech.from_pretrained(
                TTS_MODEL_ID).to(self.device)
            self.vocoder = SpeechT5HifiGan.from_pretrained(
                VOCODER_MODEL_ID).to(self.device)
        except Exception as e:
            logger.error("Failed to load SpeechT5 models: %s", e)
            raise RuntimeError(f"model_loading: SpeechT5 load failed: {e}")
        self.tts_model.eval()
        self.vocoder.eval()

        logger.info("Loading SpeechBrain ECAPA-TDNN Speaker Encoder...")
        from speechbrain.inference.speaker import EncoderClassifier
        ecapa_dir = str(ROOT / "evaluation" / "fixtures" / "ecapa_model")
        try:
            self.spk_encoder = EncoderClassifier.from_hparams(
                source=SPEAKER_ENCODER_ID,
                savedir=ecapa_dir,
                run_opts={"device": self.device},
            )
        except Exception as e:
            logger.error("Failed to load ECAPA-TDNN encoder: %s", e)
            raise RuntimeError(f"model_loading: ECAPA load failed: {e}")

        # Optional local ASR (whisper-tiny). Non-fatal if unavailable.
        try:
            from transformers import WhisperForConditionalGeneration, WhisperProcessor
            logger.info("Loading local ASR model (%s)...", ASR_MODEL_ID)
            self.asr_processor = WhisperProcessor.from_pretrained(ASR_MODEL_ID)
            self.asr_model = WhisperForConditionalGeneration.from_pretrained(
                ASR_MODEL_ID).to(self.device)
            self.asr_model.eval()
            self.asr_available = True
            logger.info("Local ASR model loaded.")
        except Exception as e:
            self.asr_available = False
            self.asr_reason = f"ASR model unavailable: {e}"
            logger.warning(self.asr_reason)

    def extract_embedding_512(self, waveform: torch.Tensor,
                              sample_rate: int) -> torch.Tensor:
        """Extract 512-dim speaker embedding formatted for SpeechT5 conditioning.

        ECAPA-TDNN yields a 192-dim L2-normalized vector; it is zero-padded
        to 512-dim as documented above (non-standard, limitation noted).
        """
        emb_192 = extract_speaker_embedding(waveform, sample_rate,
                                            self.spk_encoder)
        emb_512 = F.pad(emb_192, (0, 512 - emb_192.shape[0]))
        return emb_512.unsqueeze(0).to(self.device)

    def synthesize(self, text: str,
                   speaker_embedding_512: torch.Tensor) -> torch.Tensor:
        """Synthesize cloned speech from text and 512-dim speaker embedding."""
        inputs = self.tts_processor(text=text, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self.device)
        with torch.no_grad():
            speech = self.tts_model.generate_speech(
                input_ids,
                speaker_embedding_512,
                vocoder=self.vocoder,
            )
        out = speech.detach().cpu()
        if out.dim() == 1:
            out = out.unsqueeze(0)
        return out

    def transcribe(self, waveform: torch.Tensor,
                   sample_rate: int = 16000) -> Optional[str]:
        """Transcribe audio waveform using local Whisper-tiny. None if N/A."""
        if not self.asr_available:
            return None
        import torchaudio
        mono = waveform.mean(dim=0, keepdim=True) if waveform.dim() == 2 else waveform
        if mono.dim() == 1:
            mono = mono.unsqueeze(0)
        if sample_rate != 16000:
            mono = torchaudio.transforms.Resample(sample_rate, 16000)(mono)
        mono_np = mono.squeeze(0).cpu().numpy().astype(np.float32)
        feats = self.asr_processor(
            mono_np, sampling_rate=16000, return_tensors="pt")
        input_features = feats.input_features.to(self.device)
        with torch.no_grad():
            pred_ids = self.asr_model.generate(input_features)
        text = self.asr_processor.batch_decode(
            pred_ids, skip_special_tokens=True)[0]
        return text.strip()


@dataclasses.dataclass
class VoiceCloningTrialResult:
    speaker_id: str
    ref_utt_id: str
    target_text: str
    condition: str  # 'original_ref', 'protected_ref', 'unrelated_ref'
    cloned_audio_path: str
    status: str     # 'SUCCESS', 'FAILED'
    failure_category: Optional[str]
    failure_reason: Optional[str]
    clone_duration_s: float
    clipping_count: int
    nan_inf_count: int
    speaker_similarity_to_ref: Optional[float]
    asr_transcript: Optional[str]
    wer_score: Optional[float]


def classify_failure(exc: Exception, stage: str) -> str:
    msg = str(exc).lower()
    if "model_loading" in msg or "load" in stage:
        return "model_loading"
    if "duration" in msg or "too short" in msg:
        return "insufficient_reference_duration"
    if "preprocess" in stage or "reference" in stage:
        return "reference_preprocessing"
    if "synth" in stage or "generate" in msg:
        return "synthesis_failure"
    if "nan" in msg or "inf" in msg or "invalid" in msg or "empty" in msg:
        return "invalid_output"
    if "eval" in stage or "embedding" in msg or "transcri" in msg:
        return "evaluation_failure"
    return "other"


def build_manifest(dataset_path: Path, protected_audio_dir: Path,
                   speakers: List[str],
                   refs_per_speaker: int) -> List[Dict]:
    """Deterministic evaluation manifest (sorted, reproducible)."""
    import re
    manifest = []
    for spk_id in sorted(speakers):
        ref_files = sorted(dataset_path.glob(f"{spk_id}_*.wav"))
        # Exclude any previously protected outputs if present in dataset dir
        ref_files = [f for f in ref_files if "protected" not in f.name][:refs_per_speaker]
        others = [s for s in sorted(speakers) if s != spk_id]
        unrelated_spk = others[0] if others else spk_id
        unrelated_files = sorted(dataset_path.glob(f"{unrelated_spk}_*.wav"))
        unrelated_files = [f for f in unrelated_files if "protected" not in f.name]
        unrelated_ref = str(unrelated_files[0]) if unrelated_files else None
        for ref in ref_files:
            prot = protected_audio_dir / f"{ref.stem}_protected.wav"
            for p_idx, prompt in enumerate(EVAL_PROMPTS, 1):
                for cond in ("original_ref", "protected_ref", "unrelated_ref"):
                    manifest.append({
                        "speaker_id": spk_id,
                        "ref_file": str(ref),
                        "protected_ref_file": str(prot),
                        "unrelated_ref_file": unrelated_ref,
                        "unrelated_speaker_id": unrelated_spk,
                        "prompt_index": p_idx,
                        "prompt_text": prompt,
                        "condition": cond,
                    })
    # Deterministic ordering
    manifest.sort(key=lambda m: (m["speaker_id"], m["ref_file"],
                                 m["prompt_index"], m["condition"]))
    return manifest


def run_voice_cloning_experiment(
    dataset_dir: str = "evaluation/datasets/librispeech_benchmark",
    results_dir: str = "evaluation/results",
    device: str = "cpu",
    refs_per_speaker: int = 2,
):
    dataset_path = Path(dataset_dir) if Path(dataset_dir).is_absolute() else ROOT / dataset_dir
    results_path = Path(results_dir) if Path(results_dir).is_absolute() else ROOT / results_dir

    protected_audio_dir = results_path / "protected_audio"
    clones_dir = results_path / "cloned_audio"
    clones_dir.mkdir(parents=True, exist_ok=True)

    try:
        pipeline = VoiceCloningPipeline(device=device)
    except RuntimeError as e:
        # Model loading failure: record single failure entry and exit
        trials: List[VoiceCloningTrialResult] = []
        failures = {"model_loading": 1}
        write_json_report(results_path / "voice_cloning_results.json", trials,
                          failures, 0.0, str(e), asr_available=False,
                          manifest=[])
        write_csv_report(results_path / "voice_cloning_results.csv", trials)
        write_markdown_report(results_path / "voice_cloning_summary.md", trials,
                              failures, 0.0, str(e), asr_available=False)
        logger.error("Aborting: %s", e)
        return

    ref_files = sorted([f for f in dataset_path.glob("*.wav")
                        if "protected" not in f.name])
    if not ref_files:
        logger.error(f"No WAV audio files found in {dataset_path}")
        return

    spk_groups: Dict[str, List[Path]] = defaultdict(list)
    for f in ref_files:
        # speaker id is first two stem tokens: spk_XXXX
        parts = f.stem.split("_")
        spk_id = f"{parts[0]}_{parts[1]}"
        spk_groups[spk_id].append(f)
    for spk in spk_groups:
        spk_groups[spk] = sorted(spk_groups[spk])
    speakers = sorted(spk_groups.keys())
    logger.info(f"Loaded {len(speakers)} speakers for voice cloning evaluation: {speakers}")

    manifest = build_manifest(dataset_path, protected_audio_dir, speakers,
                              refs_per_speaker)
    with open(results_path / "voice_cloning_manifest.json", "w") as f:
        json.dump({"model": {"tts": TTS_MODEL_ID, "revision": TTS_REVISION,
                             "vocoder": VOCODER_MODEL_ID,
                             "license": MODEL_LICENSE},
                   "asr_model": ASR_MODEL_ID,
                   "asr_available": pipeline.asr_available,
                   "device": device,
                   "refs_per_speaker": refs_per_speaker,
                   "prompts": EVAL_PROMPTS,
                   "trials": manifest}, f, indent=2)
    logger.info(f"Deterministic manifest written: {len(manifest)} planned trials.")

    trials: List[VoiceCloningTrialResult] = []
    failure_counts: Dict[str, int] = defaultdict(int)
    # Cache reference embeddings per (path) to avoid recomputation
    emb_cache: Dict[str, torch.Tensor] = {}
    gt_cache: Dict[str, torch.Tensor] = {}

    def get_cond_embedding(wave: torch.Tensor, sr: int, key: str) -> torch.Tensor:
        if key not in emb_cache:
            if wave.shape[-1] < 1600:
                raise ValueError("insufficient reference duration (<0.1s)")
            emb_cache[key] = pipeline.extract_embedding_512(wave, sr)
        return emb_cache[key]

    t_start = time.time()
    # Group manifest by (speaker, ref) to load each reference once
    from itertools import groupby
    manifest_sorted = sorted(manifest, key=lambda m: (m["speaker_id"], m["ref_file"]))

    # Precompute unrelated reference embeddings
    for key, group in groupby(manifest_sorted,
                              key=lambda m: (m["speaker_id"], m["ref_file"])):
        spk_id, ref_path = key
        items = list(group)
        ref_orig_path = Path(ref_path)
        utt_id = ref_orig_path.stem
        ref_prot_path = protected_audio_dir / f"{utt_id}_protected.wav"
        unrelated_path = Path(items[0]["unrelated_ref_file"]) if items[0]["unrelated_ref_file"] else None

        # --- Load references (stage: reference_preprocessing) ---
        try:
            orig_wave, orig_sr = load_audio(str(ref_orig_path))
        except Exception as e:
            cat = "reference_preprocessing"
            failure_counts[cat] += len(items)
            for it in items:
                trials.append(VoiceCloningTrialResult(
                    speaker_id=spk_id, ref_utt_id=utt_id,
                    target_text=it["prompt_text"], condition=it["condition"],
                    cloned_audio_path="", status="FAILED",
                    failure_category=cat, failure_reason=f"orig load: {e}",
                    clone_duration_s=0.0, clipping_count=0, nan_inf_count=0,
                    speaker_similarity_to_ref=None, asr_transcript=None,
                    wer_score=None))
            continue
        try:
            prot_wave, prot_sr = load_audio(str(ref_prot_path))
        except Exception as e:
            cat = "reference_preprocessing"
            # Only protected_ref trials fail; others can proceed
            logger.warning(f"Protected reference missing for {utt_id}: {e}")
            prot_wave, prot_sr = None, None
        try:
            unrel_wave, unrel_sr = load_audio(str(unrelated_path)) if unrelated_path else (None, None)
        except Exception as e:
            logger.warning(f"Unrelated reference load failed: {e}")
            unrel_wave, unrel_sr = None, None

        # --- Ground-truth + conditioning embeddings (stage: evaluation) ---
        try:
            gt_key = f"gt::{ref_orig_path}"
            if gt_key not in gt_cache:
                gt_cache[gt_key] = extract_speaker_embedding(
                    orig_wave, orig_sr, pipeline.spk_encoder)
            gt_emb = gt_cache[gt_key]
            emb_orig = get_cond_embedding(orig_wave, orig_sr, f"orig::{ref_orig_path}")
            emb_prot = (get_cond_embedding(prot_wave, prot_sr, f"prot::{ref_prot_path}")
                        if prot_wave is not None else None)
            emb_unrel = (get_cond_embedding(unrel_wave, unrel_sr, f"unrel::{unrelated_path}")
                         if unrel_wave is not None else None)
        except Exception as e:
            cat = classify_failure(e, "evaluation")
            failure_counts[cat] += len(items)
            for it in items:
                trials.append(VoiceCloningTrialResult(
                    speaker_id=spk_id, ref_utt_id=utt_id,
                    target_text=it["prompt_text"], condition=it["condition"],
                    cloned_audio_path="", status="FAILED",
                    failure_category=cat, failure_reason=str(e)[:300],
                    clone_duration_s=0.0, clipping_count=0, nan_inf_count=0,
                    speaker_similarity_to_ref=None, asr_transcript=None,
                    wer_score=None))
            continue

        cond_map = {"original_ref": emb_orig, "protected_ref": emb_prot,
                    "unrelated_ref": emb_unrel}
        for it in items:
            cond = it["condition"]
            prompt = it["prompt_text"]
            safe_utt = "".join(c if (c.isalnum() or c in "-_") else "_" for c in utt_id)
            out_clone_path = clones_dir / f"{spk_id}_{safe_utt}_p{it['prompt_index']}_{cond}.wav"
            cond_emb = cond_map.get(cond)
            if cond_emb is None:
                cat = ("reference_preprocessing" if cond in ("protected_ref", "unrelated_ref")
                       else "evaluation_failure")
                failure_counts[cat] += 1
                trials.append(VoiceCloningTrialResult(
                    speaker_id=spk_id, ref_utt_id=utt_id, target_text=prompt,
                    condition=cond, cloned_audio_path=str(out_clone_path),
                    status="FAILED", failure_category=cat,
                    failure_reason=f"missing conditioning embedding for {cond}",
                    clone_duration_s=0.0, clipping_count=0, nan_inf_count=0,
                    speaker_similarity_to_ref=None, asr_transcript=None,
                    wer_score=None))
                continue
            try:
                cloned_wave = pipeline.synthesize(prompt, cond_emb)
                cloned_sr = 16000
                if cloned_wave.numel() == 0:
                    raise ValueError("invalid output: empty synthesis")
                nan_inf = int(torch.isnan(cloned_wave).sum().item()
                              + torch.isinf(cloned_wave).sum().item())
                if nan_inf > 0:
                    raise ValueError(f"invalid output: {nan_inf} NaN/Inf samples")
                clipping = int((cloned_wave.abs() > 0.999).sum().item())
                dur_s = round(cloned_wave.shape[-1] / cloned_sr, 3)
                sf.write(str(out_clone_path),
                         cloned_wave.squeeze(0).numpy(), cloned_sr, subtype="PCM_16")
            except Exception as e:
                cat = classify_failure(e, "synthesis")
                failure_counts[cat] += 1
                trials.append(VoiceCloningTrialResult(
                    speaker_id=spk_id, ref_utt_id=utt_id, target_text=prompt,
                    condition=cond, cloned_audio_path=str(out_clone_path),
                    status="FAILED", failure_category=cat,
                    failure_reason=str(e)[:300],
                    clone_duration_s=0.0, clipping_count=0, nan_inf_count=0,
                    speaker_similarity_to_ref=None, asr_transcript=None,
                    wer_score=None))
                continue
            try:
                cloned_emb = extract_speaker_embedding(
                    cloned_wave.unsqueeze(0) if cloned_wave.dim() == 1 else cloned_wave,
                    cloned_sr, pipeline.spk_encoder)
                spk_sim = round(float(torch.dot(gt_emb, cloned_emb).item()), 4)
            except Exception as e:
                cat = classify_failure(e, "evaluation")
                failure_counts[cat] += 1
                trials.append(VoiceCloningTrialResult(
                    speaker_id=spk_id, ref_utt_id=utt_id, target_text=prompt,
                    condition=cond, cloned_audio_path=str(out_clone_path),
                    status="FAILED", failure_category=cat,
                    failure_reason=f"clone embedding: {e}"[:300],
                    clone_duration_s=dur_s, clipping_count=clipping,
                    nan_inf_count=nan_inf,
                    speaker_similarity_to_ref=None, asr_transcript=None,
                    wer_score=None))
                continue
            # ASR is optional; WER=None when unavailable
            try:
                transcript = pipeline.transcribe(cloned_wave, cloned_sr)
                wer = compute_wer(prompt, transcript) if transcript is not None else None
                wer = round(wer, 4) if wer is not None else None
            except Exception as e:
                transcript, wer = f"ASR_ERROR: {e}"[:200], None
            trials.append(VoiceCloningTrialResult(
                speaker_id=spk_id, ref_utt_id=utt_id, target_text=prompt,
                condition=cond, cloned_audio_path=str(out_clone_path),
                status="SUCCESS", failure_category=None, failure_reason=None,
                clone_duration_s=dur_s, clipping_count=clipping,
                nan_inf_count=nan_inf,
                speaker_similarity_to_ref=spk_sim,
                asr_transcript=transcript, wer_score=wer))

    elapsed_s = round(time.time() - t_start, 2)
    logger.info(f"Voice cloning experiment completed in {elapsed_s}s: {len(trials)} trials.")
    write_json_report(results_path / "voice_cloning_results.json", trials,
                      dict(failure_counts), elapsed_s, "",
                      asr_available=pipeline.asr_available,
                      manifest=manifest)
    write_csv_report(results_path / "voice_cloning_results.csv", trials)
    write_markdown_report(results_path / "voice_cloning_summary.md", trials,
                          dict(failure_counts), elapsed_s, "",
                          asr_available=pipeline.asr_available)


def write_json_report(json_path: Path, trials: List[VoiceCloningTrialResult],
                      failures: Dict[str, int], elapsed_s: float,
                      error: str = "", asr_available: bool = False,
                      manifest: Optional[List[Dict]] = None):
    import transformers, torch as _torch
    import torchaudio as _ta
    data = {
        "metadata": {
            "cloning_model": TTS_MODEL_ID,
            "cloning_revision": TTS_REVISION,
            "vocoder": VOCODER_MODEL_ID,
            "model_license": MODEL_LICENSE,
            "transformers_version": transformers.__version__,
            "torch_version": _torch.__version__,
            "torchaudio_version": _ta.__version__,
            "speaker_encoder": SPEAKER_ENCODER_ID,
            "asr_model": ASR_MODEL_ID,
            "asr_available": asr_available,
            "device": "cpu",
            "total_trials": len(trials),
            "successful_trials": sum(1 for t in trials if t.status == "SUCCESS"),
            "failed_trials": sum(1 for t in trials if t.status == "FAILED"),
            "elapsed_seconds": elapsed_s,
            "error": error,
            "conditioning_note": ("512-dim SpeechT5 conditioning = L2-normalized "
                                  "ECAPA-TDNN 192-dim zero-padded to 512-dim "
                                  "(non-standard surrogate proxy; see module docstring)."),
            "quality_note": ("STOI and source-vs-clone SNR/SI-SDR are not reported: "
                             "source and clone differ in linguistic content and "
                             "synthesis pipeline, so waveform-aligned ratios are "
                             "not meaningful. Duration/clipping/NaN-Inf reported."),
        },
        "failure_classification": dict(failures),
        "trials": [dataclasses.asdict(t) for t in trials],
    }
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)


def write_csv_report(csv_path: Path, trials: List[VoiceCloningTrialResult]):
    fieldnames = [
        "speaker_id", "ref_utt_id", "condition", "status", "failure_category",
        "failure_reason", "clone_duration_s", "clipping_count", "nan_inf_count",
        "speaker_similarity_to_ref", "wer_score", "asr_transcript", "target_text",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in trials:
            d = dataclasses.asdict(t)
            d.pop("cloned_audio_path", None)
            writer.writerow(d)


def _fmt(x: Optional[float]) -> str:
    return f"{x:.4f}" if x is not None else "n/a"


def write_markdown_report(md_path: Path, trials: List[VoiceCloningTrialResult],
                          failures: Dict[str, int], elapsed_s: float,
                          error: str = "", asr_available: bool = False):
    succ = [t for t in trials if t.status == "SUCCESS"]

    def sims(cond):
        return [t.speaker_similarity_to_ref for t in succ
                if t.condition == cond and t.speaker_similarity_to_ref is not None]

    def wers(cond):
        return [t.wer_score for t in succ
                if t.condition == cond and t.wer_score is not None]

    orig_sims, prot_sims, ctrl_sims = sims("original_ref"), sims("protected_ref"), sims("unrelated_ref")
    orig_wers, prot_wers = wers("original_ref"), wers("protected_ref")
    o_s, p_s, c_s = _stats(orig_sims), _stats(prot_sims), _stats(ctrl_sims)

    succ_durs = [t.clone_duration_s for t in succ]
    tot_clip = sum(t.clipping_count for t in succ)
    tot_nan = sum(t.nan_inf_count for t in succ)

    lines = [
        "# AudioShield Downstream Voice-Cloning Evaluation Summary",
        "",
        "## Model documentation (reproducibility)",
        "",
        f"- **Cloning model**: `{TTS_MODEL_ID}` (rev `{TTS_REVISION}`) + `{VOCODER_MODEL_ID}`",
        f"- **License**: {MODEL_LICENSE}; weights downloaded from HuggingFace Hub at runtime (not committed to Git)",
        "- **Libraries**: `transformers` 4.57.6, `torch` 2.8.0 / `torchaudio` 2.8.0, `speechbrain` 1.1.1, CPU, `eval` mode, `torch.no_grad()`",
        "- **Inference command**: `.venv/bin/python evaluation/voice_cloning_eval.py --dataset-dir evaluation/datasets/librispeech_benchmark --results-dir evaluation/results --device cpu`",
        "- **Conditioning**: ECAPA-TDNN 192-dim (L2-norm) zero-padded to SpeechT5 512-dim (non-standard surrogate proxy)",
        f"- **ASR model**: `{ASR_MODEL_ID}` (local, via transformers); available in this run: `{asr_available}`",
        "- **Limitations**: SpeechT5 is an embedding-conditioned TTS proxy, not a dedicated zero-shot cloner (XTTS-v2/Bark/VALL-E/OpenVoice untested); ECAPA->512 padding is non-standard; single CPU config; no subjective MOS; no source-vs-clone SNR/STOI (not meaningful across different waveforms).",
        "",
        "## Separation of claims",
        "",
        "- HuBERT representation distortion, ECAPA speaker-embedding shift, and this downstream synthesis experiment are reported separately. One is not treated as proof of another.",
        "",
        f"- **Total trials**: {len(trials)} | **Successful**: {len(succ)} | **Failed**: {len(trials) - len(succ)} | **Time**: {elapsed_s:.2f} s",
        (f"- **Setup error**: {error}" if error else ""),
        "",
        "## 1. Aggregate results",
        "",
        "| Condition | N | Speaker sim mean | Median | Std | Min | Max | WER mean (n) | Failures |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for label, st, w in (("Original ref → clone", o_s, orig_wers),
                         ("Protected ref → clone", p_s, prot_wers),
                         ("Unrelated ref → clone (control)", c_s, [])):
        wmean = f"{np.mean(w):.4f} (n={len(w)})" if w else "n/a"
        lines.append(
            f"| **{label}** | {st['n']} | **{_fmt(st['mean'])}** | {_fmt(st['median'])} | "
            f"{_fmt(st['std'])} | {_fmt(st['min'])} | {_fmt(st['max'])} | {wmean} | — |")
    lines += [
        "",
        "## 2. Per-speaker speaker-similarity breakdown (successful clones)",
        "",
        "| Speaker ID | Orig ref→clone mean (n) | Protected ref→clone mean (n) | Unrelated control mean (n) | Delta (orig−prot) |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    spk_map = defaultdict(lambda: defaultdict(list))
    for t in succ:
        if t.speaker_similarity_to_ref is not None:
            spk_map[t.speaker_id][t.condition].append(t.speaker_similarity_to_ref)
    for spk_id in sorted(spk_map.keys()):
        o = spk_map[spk_id]["original_ref"]
        p = spk_map[spk_id]["protected_ref"]
        u = spk_map[spk_id]["unrelated_ref"]
        o_m = float(np.mean(o)) if o else None
        p_m = float(np.mean(p)) if p else None
        u_m = float(np.mean(u)) if u else None
        delta = (o_m - p_m) if (o_m is not None and p_m is not None) else None
        lines.append(
            f"| `{spk_id}` | {_fmt(o_m)} (n={len(o)}) | {_fmt(p_m)} (n={len(p)}) | "
            f"{_fmt(u_m)} (n={len(u)}) | {_fmt(delta)} |")
    lines += [
        "",
        "## 3. Audio-quality of generated clones (no source-vs-clone SNR/STOI)",
        "",
        f"- Successful clones: {len(succ)}; mean duration: "
        f"{(round(float(np.mean(succ_durs)), 3) if succ_durs else 'n/a')} s",
        f"- Total clipped samples (|x|>0.999): {tot_clip}; total NaN/Inf samples: {tot_nan}",
        "- STOI / source-vs-clone SNR intentionally omitted (different linguistic content; waveform-aligned metrics not meaningful).",
        "",
        "## 4. Failure classification",
        "",
        "| Category | Count |",
        "| :--- | :--- |",
    ]
    for cat in ["model_loading", "reference_preprocessing",
                "insufficient_reference_duration", "synthesis_failure",
                "invalid_output", "evaluation_failure", "other"]:
        lines.append(f"| `{cat}` | {failures.get(cat, 0)} |")
    lines += [
        "",
        "## 5. Measured comparison (no absolute-claim language)",
        "",
    ]
    if o_s["mean"] is not None and p_s["mean"] is not None:
        lines.append(
            f"Mean source→clone speaker similarity: original-reference clones `{o_s['mean']:.4f}` "
            f"(n={o_s['n']}) vs protected-reference clones `{p_s['mean']:.4f}` (n={p_s['n']}); "
            f"unrelated-speaker control `{c_s['mean'] if c_s['mean'] is not None else 'n/a'}`. "
            f"Per-trial WER where ASR available: original {(round(float(np.mean(orig_wers)), 4) if orig_wers else 'n/a')} / "
            f"protected {(round(float(np.mean(prot_wers)), 4) if prot_wers else 'n/a')}. "
            "Sample size is small (10 speakers, 2 references each); "
            "results are reported as observed measurements with a control baseline, "
            "not as proof of prevention. No 'prevents voice cloning' / 'AI-proof' claim is made.")
    else:
        lines.append("Insufficient successful trials for a measured comparison; see failure table.")
    lines.append("")
    with open(md_path, "w") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="AudioShield Voice Cloning Evaluation")
    parser.add_argument("--dataset-dir", default="evaluation/datasets/librispeech_benchmark")
    parser.add_argument("--results-dir", default="evaluation/results")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--refs-per-speaker", type=int, default=2)
    args = parser.parse_args()

    run_voice_cloning_experiment(dataset_dir=args.dataset_dir,
                                 results_dir=args.results_dir,
                                 device=args.device,
                                 refs_per_speaker=args.refs_per_speaker)


if __name__ == "__main__":
    main()
