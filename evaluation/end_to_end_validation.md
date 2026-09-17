# AudioShield End-to-End Scientific Validation & Representation Report

---

## 1. Objective

The objective of this evaluation is to empirically measure the end-to-end performance, audio fidelity preservation, feature space distortion, speaker identity shift, and objective perceptual quality of the AudioShield voice protection pipeline. AudioShield applies a 16 kHz HuBERT-targeted Projected Gradient Descent (PGD) adversarial perturbation, projected and constrained back to the native audio rate at $\varepsilon = 0.02$.

This evaluation replaces all prior synthetic/generated speaker fixtures with a reproducible, genuine multi-speaker human speech evaluation dataset derived from the legally usable **LibriSpeech** corpus (`dev-clean`).

---

## 2. Experimental Setup

* **Operating System**: macOS (Darwin 23.x / Apple Silicon CPU)
* **Python Runtime**: Python 3.9.6 (`.venv`)
* **Machine Learning Libraries**:
  * PyTorch 2.x
  * Torchaudio
  * HuggingFace Transformers
  * SpeechBrain 1.1.1 (`speechbrain/spkrec-ecapa-voxceleb`)
  * `pystoi` 0.4.1
* **Surrogate ML Models**:
  * `facebook/hubert-base-ls960` (Layer 12 `last_hidden_state`, 768-dim embeddings)
* **Protection Pipeline Parameters**:
  * PGD $\varepsilon = 0.02$, $\alpha = 0.002$, `num_steps = 15`, `random_start = True`, `pre_emphasis = True`
  * Dual-rate architecture: Hann-window Overlap-Add (OLA) 16 kHz chunk stitching (10.0s max chunk, 0.05s overlap)
  * Native-rate resampled perturbation projection and strict hard clamping ($\delta \in [-0.02, 0.02]$).

---

## 3. Dataset (Genuine Multi-Speaker Human Speech)

Evaluation was conducted over a multi-speaker, multi-utterance, multi-duration speech benchmark dataset derived from **LibriSpeech `dev-clean`** (genuine human speech recordings):

* **Speakers**: 10 genuine human speakers (anonymized evaluation labels, canonical run 2026-09-17 — see `evaluation/results/canonical_run.json`):
  * `spk_1272`, `spk_1462`, `spk_1673`, `spk_174`, `spk_1919`, `spk_251`, `spk_422`, `spk_652`, `spk_777`, `spk_84`
  * *Superseded note*: earlier revisions of this document listed a different speaker set (`spk_1987`, `spk_2035`, `spk_2078`, `spk_2086`, `spk_2277`, `spk_2412`, `spk_2428`, …) with different metrics. Those artifacts were overwritten on 2026-09-17 (results directory is not tracked in git) and are unrecoverable; the numbers below are from the fresh canonical run, which reproduces the archived 2026-09-17 10:28 run within PGD random-start jitter.
* **Utterance Configurations per Speaker**:
  * 6 real speech utterances per speaker (60 audio files total)
  * Durations ranging from 2.09 seconds to 29.40 seconds
  * Native audio configurations:
    * 16,000 Hz sample rate, 1 channel (mono)
    * 44,100 Hz sample rate, 2 channels (stereo)
    * 48,000 Hz sample rate, 1 channel (mono)
* **Total Benchmark Size**: 60 audio files covering 16 kHz, 44.1 kHz, 48 kHz, mono, stereo, and varying durations.

---

## 4. Audio Preservation & Perturbation Statistics

All protected files were saved to disk and reloaded to evaluate dimensional preservation and perturbation statistics:

| Metric / Statistic | Measured Value | Requirement / Bound | Verdict |
| :--- | :--- | :--- | :--- |
| **Sample Rate Preservation** | 100% (60/60 match) | Native sample rate preserved | **EXACT MATCH** |
| **Channel Count Preservation** | 100% (60/60 match) | Mono / Stereo layout preserved | **EXACT MATCH** |
| **Sample Count Preservation** | 100% (60/60 match) | Exact total sample count preserved | **EXACT MATCH** |
| **Duration Preservation** | 100% ($< 0.1\text{ ms}$ delta) | Waveform duration preserved | **EXACT MATCH** |
| **$L_\infty$ Perturbation ($\max \|\delta\|$)** | **0.020000** | $\le 0.020000$ | **STRICTLY BOUNDED** |
| **RMS Perturbation** | Mean: 0.008950 (Min: 0.008128, Max: 0.009972) | — | Normal distribution |
| **Signal-to-Noise Ratio (SNR)** | **17.02 dB** (Min: 8.71 dB, Max: 22.38 dB) | Fidelity preservation | Objective ratio |
| **SI-SDR** | **16.99 dB** (Min: 8.59 dB, Max: 22.37 dB) | Scale-invariant ratio | Objective ratio |
| **Peak Amplitude** | Mean: 0.532827 | $\le 1.000000$ | Safe range |
| **Clipping Count ($|x| > 0.999$)** | **0** | 0 clipped samples | **ZERO CLIPPING** |
| **NaN / Inf Count** | **0** | 0 non-finite values | **ZERO NON-FINITE** |

---

## 5. HuBERT Feature Distortion (Layer 12)

Representation distortion measured on HuBERT Layer 12 (`last_hidden_state`, 768-dim) across all 60 genuine human speech utterances:

* **Mean Cosine Similarity**: `0.249748` (Range: 0.0702 to 0.4081)
* **Mean Cosine Distance ($1 - \text{CosSim}$)**: `0.750252`
* **Mean $L_2$ Distance**: `310.07`
* **Mean Normalized $L_2$ Distance ($\frac{\|f_{\text{orig}} - f_{\text{prot}}\|_2}{\|f_{\text{orig}}\|_2}$)**: `1.2558`

*Finding*: The PGD attack depresses HuBERT representation cosine similarity from $1.0$ down to $\sim 0.250$ on genuine human speech, achieving significant feature vector displacement within the ML surrogate model space.

---

## 6. Speaker Identity Embedding Results (ECAPA-TDNN)

Speaker identity shifts were measured using the pre-trained SpeechBrain ECAPA-TDNN (`spkrec-ecapa-voxceleb`) speaker verification encoder across pairwise speaker/utterance combinations on 10 genuine human speakers:

### Overall Distribution Statistics

| Pair Type | Mean CosSim | Std | Min | Median (50%) | Max |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Original ↔ Original (Same Speaker, Diff Utt)** | **0.7641** | 0.1229 | 0.2325 | 0.7940 | 0.9098 |
| **Original ↔ Protected (Same Utterance & Speaker)** | **0.6769** | 0.0955 | 0.4274 | 0.7031 | 0.8516 |
| **Original ↔ Other Speaker (Diff Speaker)** | **0.1102** | 0.0908 | -0.1207 | 0.1049 | 0.4962 |

### Per-Speaker Embedding Shift Breakdown

| Speaker ID | Orig ↔ Orig Mean | Orig ↔ Protected Mean | Orig ↔ Other Mean | Min Orig-Prot Sim | Max Orig-Prot Sim |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `spk_1272` | 0.8319 | 0.7417 | 0.0819 | 0.6738 | 0.8109 |
| `spk_1462` | 0.7183 | 0.5826 | 0.1278 | 0.5117 | 0.6988 |
| `spk_1673` | 0.8832 | 0.7917 | 0.1364 | 0.7569 | 0.8134 |
| `spk_174` | 0.8034 | 0.6742 | 0.0818 | 0.6198 | 0.7274 |
| `spk_1919` | 0.7922 | 0.6961 | 0.0911 | 0.6016 | 0.7857 |
| `spk_251` | 0.7222 | 0.5749 | 0.1268 | 0.5143 | 0.6671 |
| `spk_422` | 0.8232 | 0.7713 | 0.0918 | 0.7041 | 0.8516 |
| `spk_652` | 0.8342 | 0.7251 | 0.1322 | 0.7068 | 0.7519 |
| `spk_777` | 0.6347 | 0.5755 | 0.1062 | 0.4274 | 0.6593 |
| `spk_84` | 0.5976 | 0.6363 | 0.1258 | 0.5078 | 0.7148 |

*Finding*: AudioShield protection causes a systematic shift in ECAPA-TDNN speaker embeddings across genuine human speakers. The mean cosine similarity of protected audio to its original speaker drops from **0.7641** down to **0.6769**, against a baseline inter-speaker similarity of **0.1102**. The shift is smaller than previously reported from the superseded run; representation-distortion and speaker-embedding results are reported separately from downstream cloning resistance.

---

## 7. Objective Perceptual Quality

Objective speech intelligibility and quality metrics measured across all 60 genuine human speech utterances:

* **Short-Time Objective Intelligibility (STOI)**:
  * Mean: **0.9191** (Range: 0.8171 to 0.9746)
  * Indicates high objective phonetic speech intelligibility.
* **Signal-to-Noise Ratio (SNR)**: Mean **17.02 dB**.
* **Scale-Invariant Signal-to-Distortion Ratio (SI-SDR)**: Mean **16.99 dB**.
* **PESQ Limitation Note**: PESQ metric computation could not be executed because the `pesq` C-extension package is not installed in the current Python 3.9 environment. STOI and SI-SDR are reported as the primary objective perceptual quality indicators.

*Important Distinction*: High STOI ($0.9191$) and SNR ($17.02\text{ dB}$) demonstrate objective speech intelligibility and acoustic signal fidelity, but do **not** constitute formal subjective human listening claims ("imperceptibility").

---

## 8. Voice-Cloning Evaluation Status

A formal evaluation protocol has been designed and specified in `evaluation/voice_cloning_protocol.md` covering:
1. Candidate TTS Engines: Coqui XTTS-v2, Suno Bark, VALL-E X, OpenVoice.
2. Metrics: Speaker Similarity (ECAPA-TDNN), Intelligibility (Whisper WER/CER), Synthesis Quality (UTMOS, MCD).

### 8.1 Executed downstream experiment (surrogate proxy, 2026-09-17)

> **SpeechT5 surrogate proxy — negative/control experiment.** Retained as-is;
> must NOT be used as evidence for or against AudioShield's voice-cloning
> protection. It demonstrates that the surrogate cannot establish protection
> effectiveness because the original-reference baseline itself does not
> preserve speaker identity.

An actual downstream synthesis experiment was executed with a reproducible local
open-source model and is reported separately in
`evaluation/results/voice_cloning_summary.md` (+ `.json` / `.csv` / manifest):

* **Cloning model**: `microsoft/speecht5_tts` (rev `30fcde3`) + `microsoft/speecht5_hifigan`
  (Apache 2.0; weights from HuggingFace Hub, not committed to Git).
  ECAPA-TDNN 192-dim embeddings zero-padded to SpeechT5 512-dim conditioning
  (non-standard surrogate proxy — see §6 of the summary for limitations).
* **Design**: 10 genuine LibriSpeech speakers × 2 references × 3 prompts ×
  3 conditions (A original-ref, B protected-ref, C unrelated-ref control) =
  180 planned trials, deterministic manifest
  (`evaluation/results/voice_cloning_manifest.json`).
  Identical text, inference settings, and evaluation for all conditions.
* **Outcome**: 180/180 SUCCESS, 0 failures. Source→clone speaker similarity:
  original-ref `0.0504` vs protected-ref `0.0710` vs unrelated control `0.1046`
  (ECAPA-TDNN). WER (local `openai/whisper-tiny`): original `0.2766` vs
  protected `0.2662`. Clone audio: 0 clipped, 0 NaN/Inf samples; mean
  duration 3.178 s. STOI / source-vs-clone SNR deliberately omitted (different
  waveforms; not meaningful).
* **Interpretation**: the baseline itself does not achieve speaker-faithful
  cloning (`0.0504` vs `0.7641` real-speech same-speaker similarity), i.e. a
  floor effect. No measurable reduction of cloning effectiveness attributable
  to protection was observed in this proxy setup (delta in the wrong direction,
  within noise). Post-hoc original-clone↔protected-clone similarity is
  `0.6268` (generic synthesis voice). This is a valid negative/control result
  for this surrogate proxy only.

*Status*: End-to-end voice cloning synthesis against dedicated external
zero-shot TTS cloners (XTTS-v2 / Bark / VALL-E X / OpenVoice) remains
**UNVALIDATED** (see §11.5).

### 8.2 Dedicated zero-shot experiment: Coqui XTTS-v2 (2026-09-17)

* **Model**: Coqui XTTS-v2 (`tts_models/multilingual/multi-dataset/xtts_v2`,
  coqui-TTS 0.22.0, CPML non-commercial; `COQUI_TOS_AGREED=1`).
  Isolated venv `~/.venvs/audioshield-xtts` (Python 3.9, torch 2.8.0,
  transformers 4.46.3) — required because coqui-TTS pins (`numpy==1.22`,
  spacy build) conflict with the main `.venv`; main env untouched
  (`pip check` clean). Weights downloaded at runtime (~2 GB), not in Git.
  Documented workarounds: `--no-deps` install + runtime-only deps,
  `bangla`-package `__future__` patch (3.10+ syntax, off the English path),
  torch-2.6+ `weights_only` config-class allowlist, pinned sampling
  (`temperature=0.65, top_k=50, top_p=0.85, length_penalty=1.0,
  repetition_penalty=2.0, speed=1.0`, `torch.manual_seed(0)`, CPU).
* **Design** (`evaluation/xtts_synthesize.py` + `evaluation/xtts_evaluate.py`):
  10 canonical LibriSpeech speakers × longest reference each × 2 fixed prompts
  × 3 conditions (A original, B protected, C unrelated-speaker control) =
  60 clones, identical text/params/seed/procedure. Manifest:
  `evaluation/results/xtts_clones/xtts_manifest.json`. Results:
  `evaluation/results/xtts_full_results.json/.csv`,
  `evaluation/results/xtts_full_summary.md`
  (baseline-only cut: `xtts_baseline_*`).
* **Phase-4 baseline (original refs)**: source→clone ECAPA similarity mean
  **0.5953** (median 0.6183, std 0.0879, range 0.3957–0.7398, n=20) vs
  canonical same-speaker 0.7641 / cross-speaker 0.1102 — verdict
  `BASELINE_SPEAKER_FAITHFUL` for all 10 speakers (per-speaker 0.45–0.73).
  The gate PASSED; protection testing was valid to proceed.
* **Phase-5 protected refs**: mean **0.3892** (median 0.4064, std 0.1014,
  range 0.1635–0.5323, n=20). **Unrelated control**: mean **0.0962**
  (median 0.0975, n=20) — at the canonical chance level (0.1102), validating
  the measurement. The protected drop (Δ −0.206) is directionally consistent
  across all 10 speakers but does not reach the control floor (partial, not
  complete, identity reduction).
* **WER** (local whisper-tiny): original 0.3014 / protected 0.2104 /
  unrelated 0.7285 (means; medians 0.25/0.2361/0.4166). High-WER trials in all
  conditions show XTTS autoregressive continuation rambling past the prompt
  (prompt prefix correctly produced); WER is confounded by this behavior and
  shows no protection-induced intelligibility loss.
* **Clone validity**: 60/60 synthesis OK, 0 failures; 0 NaN/Inf; 64 clipped
  samples total (negligible); durations 3.1–27.1 s (long tail = rambling
  trials). Source-vs-clone SNR/STOI omitted (different waveforms).
* **Interpretation**: first interpretable downstream evidence of reduced
  cloning effectiveness under a valid baseline — preliminary, single model,
  small N (n=20/condition, 1 reference/speaker). No prevention claim.

### 8.3 Replication: 3 references × 3 PGD seeds, paired analysis (2026-09-17)

* **Design**: same XTTS-v2 model/weights/prompts/sampling as §8.2; 10 speakers
  × 3 longest references × 2 prompts × 5 conditions
  (original, protected seeds {0,1,2}, unrelated control) = 300 clones, 60
  complete pairs. Protected variants generated with the unmodified pipeline
  under `torch.manual_seed(seed)` (single-threaded); per-pair RNG reseeding
  (torch+numpy+random from pair hash) keeps conditions RNG-fair.
  Scripts: `evaluation/xtts_rep_protect.py`, `xtts_rep_synthesize.py`
  (2 parallel workers, disjoint speaker sets, merged with
  `evaluation/xtts_rep_merge.py`), `evaluation/xtts_rep_evaluate.py`.
  Results: `evaluation/results/xtts_rep_results.json/.csv`,
  `evaluation/results/xtts_rep_summary.md`.
* **Condition means** (ECAPA source→clone): original **0.5483**; protected
  seed0 **0.3283** / seed1 **0.3603** / seed2 **0.3430**; unrelated **0.0852**.
* **Paired Deltas** (original − protected, n=60 pairs/seed): seed0 **0.2200**
  95% CI [0.1855, 0.2544]; seed1 **0.1880** [0.1613, 0.2147]; seed2 **0.2052**
  [0.1710, 0.2395]. Paired-t p ≈ 1e-18–1e-20, Wilcoxon p ≈ 1e-11,
  Cohen's dz 1.55–1.82. Sign consistency: 59/60, 60/60, 57/60 pairs and
  **10/10 speakers positive on all three seeds** (magnitudes vary:
  spk_174 ~0.37, spk_1673/spk_1919 ~0.06–0.15). Unrelated paired Delta 0.4631 —
  the protection effect (~0.20) is less than half the full identity gap
  (partial reduction, consistent with §8.2).
* **WER**: medians identical across original/seed0/seed1/seed2 (**0.25**);
  seed0 mean (0.74) is a single catastrophic repetition-degeneration trial
  ("I, I, I…", WER 27.75). No systematic intelligibility loss.
* **Validity**: 300/300 synthesis OK, 0 failures, 0 NaN/Inf. Status remains
  **PRELIMINARY** (single engine; multi-engine replication still open).

---

## 9. Limitations

1. **Surrogate Model Overfitting**: Adversarial perturbations are optimized against HuBERT base (`facebook/hubert-base-ls960`). Transferability to alternative self-supervised representations (WavLM, wav2vec2, EnCodec) is unverified.
2. **Environment Metric Gaps**: PESQ metric library was unavailable in the test environment.
3. **No Subjective MOS**: Objective metrics (STOI, SNR, SI-SDR) are available, but subjective human Mean Opinion Score (MOS) listening tests have not been conducted.

---

## 10. Reproducibility

The complete genuine human speech benchmark can be re-run deterministically with a single command:

```bash
.venv/bin/python evaluation/benchmark.py --dataset-dir evaluation/datasets/librispeech_benchmark --results-dir evaluation/results --device cpu
```

Unit and integration regression tests can be run via:

```bash
.venv/bin/python -m pytest tests/ -v
AUDIOSHIELD_RUN_SLOW_TESTS=1 .venv/bin/python -m pytest tests/ --run-slow -v
git diff --check
.venv/bin/python -m pip check
```

---

## 11. Conclusions & Explicit Validation Categorization

### Explicit Validation Categorization

1. **ENGINEERING VALIDATION**: **VALIDATED**
   - 16k, 44.1k, 48k mono/stereo sample rate, channel count, sample count, and duration preservation fully verified. Strict native-rate perturbation constraint $\varepsilon = 0.020000$ enforced without clipping or NaN/Inf values.

2. **ML REPRESENTATION VALIDATION**: **VALIDATED**
   - HuBERT Layer 12 representation cosine similarity is systematically depressed from $1.0$ to $0.2497$ on genuine multi-speaker human speech.

3. **SPEAKER-IDENTITY VALIDATION**: **PRELIMINARY**
   - ECAPA-TDNN speaker vector similarity drops from $0.7641$ (original) to $0.6769$ (protected) across 10 genuine human speakers, against an inter-speaker baseline of $0.1102$. Marked as PRELIMINARY pending downstream voice-cloning synthesis validation.

4. **PERCEPTUAL QUALITY VALIDATION**: **PARTIALLY VALIDATED (OBJECTIVE ONLY)**
   - Objective intelligibility (STOI = $0.9191$) and fidelity (SNR = $17.02\text{ dB}$) verified. Subjective human MOS listening tests remain unconducted.

5. **VOICE-CLONING VALIDATION**: **PRELIMINARY**
   - A SpeechT5 surrogate-proxy experiment (180 trials) is retained as a
     negative control (floor effect, uninterpretable).
   - A dedicated zero-shot experiment (Coqui XTTS-v2, 60 clones, §8.2) met the
     Phase-4 gate with a speaker-faithful baseline (source→clone 0.5953 vs
     cross-speaker 0.1102) and produced interpretable results: protected
     references yield consistently lower clone similarity (0.3892, Δ −0.206 in
     all 10 speakers) without reaching the unrelated floor (0.0962).
   - PRELIMINARY, not VALIDATED: single cloning architecture, and no
     multi-engine replication (Bark / VALL-E X / OpenVoice untested).
     A 3-reference × 3-seed paired replication (300 clones, §8.3) confirms the
     effect (per-seed Δ 0.19–0.22, CIs exclude zero, 10/10 speakers positive
     on all seeds) but does not change the single-engine limitation.
     No "prevents voice cloning" claim is made.

---

## 12. Final Report Summary

1. **Dataset Used**: LibriSpeech `dev-clean` (Genuine Multi-Speaker Human Speech Corpus)
2. **Number of Speakers**: 10 genuine human speakers (`spk_1272`, `spk_1462`, `spk_1673`, `spk_174`, `spk_1919`, `spk_251`, `spk_422`, `spk_652`, `spk_777`, `spk_84`)
3. **Number of Utterances**: 60 real human speech clips (6 per speaker, spanning 2.09s to 29.40s, 16k/44.1k/48k mono/stereo)
4. **Exact Commands**:
   - Benchmark: `.venv/bin/python evaluation/benchmark.py --dataset-dir evaluation/datasets/librispeech_benchmark --results-dir evaluation/results --device cpu`
   - Regression unit tests: `.venv/bin/python -m pytest tests/ -v`
   - Regression slow tests: `AUDIOSHIELD_RUN_SLOW_TESTS=1 .venv/bin/python -m pytest tests/ --run-slow -v`
   - Code formatting check: `git diff --check`
   - Dependency integrity check: `.venv/bin/python -m pip check`
5. **Aggregate Metrics**:
   - $L_\infty$ Perturbation: **0.020000** (Strictly Bounded)
   - SNR / SI-SDR: **17.02 dB / 16.99 dB**
   - STOI Score: **0.9191**
   - HuBERT Layer 12 Cosine Similarity: **0.2497** (Cosine Distance: **0.7503**)
   - ECAPA-TDNN Same Speaker Original-Original: **0.7641**
   - ECAPA-TDNN Same Utterance Original-Protected: **0.6769**
   - ECAPA-TDNN Different Speaker Original-Other: **0.1102**
6. **Per-Speaker Metrics**: Detailed per-speaker table for all 10 speakers included in Section 6.
7. **Comparison with earlier runs**: The canonical 2026-09-17 run reproduces the archived 2026-09-17 10:28 run within PGD random-start jitter (HuBERT cosine similarity 0.2497 vs 0.2508; ECAPA orig↔prot 0.6769 vs 0.6768), confirming the pipeline is stable on natural human speech. Still-earlier figures quoted in prior revisions of this document (HuBERT ~0.298, ECAPA 0.9575/0.5429/0.4670) came from a superseded speaker subset whose artifacts were overwritten and are unrecoverable; they are not directly comparable.
8. **Limitations**:
   - Adversarial optimization target is limited to HuBERT base (`facebook/hubert-base-ls960`).
   - PESQ metric unavailable due to missing `pesq` C-extension in `.venv`.
   - Subjective human MOS listening tests remain unconducted.
9. **Proceeding to Voice-Cloning Evaluation**: **YES, with a valid-baseline gate**. The empirical evidence on genuine multi-speaker human speech confirms ML representation distortion and a moderate speaker embedding shift while preserving high objective acoustic fidelity ($\text{SNR} = 17.02\text{ dB}$, $\text{STOI} = 0.9191$). A SpeechT5 surrogate-proxy experiment was completed as a negative control (floor effect, no interpretability). Dedicated zero-shot cloning evaluation (XTTS-v2) may proceed ONLY after demonstrating a speaker-faithful original-reference baseline (Phase 4 gate).
10. **XTTS-v2 downstream cloning (2026-09-17)**: baseline source→clone **0.5953** (gate PASSED); protected **0.3892**; unrelated control **0.0962** (n=20/condition, ECAPA-TDNN); WER original 0.3014 / protected 0.2104 (confounded by XTTS continuation rambling); 60/60 synthesis OK. Voice-cloning validation: **PRELIMINARY** (single engine, small N — see §11.5).
11. **XTTS-v2 paired replication (2026-09-17)**: 10 speakers × 3 refs × 3 PGD seeds × 2 prompts = 300/300 clones OK; condition means original **0.5483**, protected **0.3283/0.3603/0.3430**, unrelated **0.0852**; paired Δ per seed **0.2200/0.1880/0.2052** (95% CIs exclude zero; paired-t p≈1e-18–1e-20; Wilcoxon p≈1e-11; dz 1.55–1.82); 59–60/60 pairs and 10/10 speakers positive on every seed; WER medians identical (0.25) across original/protected. Status: **PRELIMINARY** (single engine — see §§8.3/11.5).
