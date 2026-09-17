# AudioShield Voice-Cloning Resistance Evaluation Protocol

## 1. Executive Summary & Objective

This document defines the formal, scientific evaluation protocol for testing AudioShield against real downstream zero-shot and few-shot voice-cloning text-to-speech (TTS) systems.

The core objective is to compare:
- **Baseline Path**: Original speech $\rightarrow$ Voice-Cloning Engine $\rightarrow$ Cloned Voice Output ($A$)
- **Protected Path**: Protected speech $\rightarrow$ Voice-Cloning Engine $\rightarrow$ Cloned Voice Output ($B$)

---

## 2. Distinction of Validation Claims

To maintain scientific integrity, the following three tiers of validation claims are strictly separated and must **never** be conflated:

1. **HuBERT Representation Distortion (ML Feature Space)**:
   - Measures direct feature embedding degradation in self-supervised speech encoder representations (e.g., HuBERT Layer 12 `last_hidden_state`).
   - *Scope*: Internal ML perturbation efficiency. Does **not** guarantee voice cloning prevention on external architectures.

2. **Speaker Verification Degradation (Speaker Identity Space)**:
   - Measures cosine similarity shift in standalone speaker verification encoders (e.g., ECAPA-TDNN, d-vector, Res2Net-VoxCeleb).
   - *Scope*: Speaker verification bypass/confusion. Does **not** measure acoustic synthesis quality of generated clones.

3. **Actual Voice-Cloning Resistance (Downstream TTS Synthesis)**:
   - Measures output speech quality, speaker fidelity, and intelligibility of voices cloned from protected audio.
   - *Scope*: True end-to-end protective efficacy against malicious voice cloning.

---

## 3. Target Model Families & Architectures

Evaluation must encompass multiple distinct voice-cloning model families to prevent overfitting:

| Family | Architecture Type | Representative Models | Conditioning Mechanism |
| :--- | :--- | :--- | :--- |
| **Autoregressive Audio LM** | Neural Codec + Language Model | Suno Bark, VALL-E X | Encodec / DAC tokens conditioned on prompt audio |
| **Diffusion / Flow Matching** | Latent Diffusion / Flow Matching | Coqui XTTS-v2, Voicebox, E2 TTS | Mel-spectrogram latents + Performer/Transformer |
| **Feature Extraction + Vocoder** | Separate Encoder + FastSpeech2 / HiFi-GAN | OpenVoice, Resemblyzer + Tacotron2 | Fixed speaker embedding vector + mel synthesis |

---

## 4. Evaluation Metrics & Quantifiable Criteria

For every test speaker $s$, given prompt prompt audio $x_{\text{orig}}$ and protected prompt audio $x_{\text{prot}}$, candidate clones $y_{\text{orig}} = \text{TTS}(x_{\text{orig}}, \text{text})$ and $y_{\text{prot}} = \text{TTS}(x_{\text{prot}}, \text{text})$ are generated for standardized test scripts.

### A. Speaker Identity Similarity
- **Metric**: Cosine similarity $\cos(E(y_{\text{prot}}), E(x_{\text{orig}}))$ using pre-trained ECAPA-TDNN ($E$).
- **Success Indicator**: Significant drop in speaker embedding similarity of $y_{\text{prot}}$ relative to reference speaker $x_{\text{orig}}$.

### B. Speech Intelligibility & Transcription Quality
- **Metric**: Word Error Rate (WER) and Character Error Rate (CER) computed using automatic speech recognition (Whisper Large-v3).
- **Formula**:
  $$\text{WER} = \frac{S + D + I}{N}$$
- **Success Indicator**: Increased WER/CER in $y_{\text{prot}}$ indicates severe phonetic corruption or unintelligible clone synthesis.

### C. Synthesis Quality & Acoustic Artifacts
- **Metrics**:
  - **UTMOS** (MOS prediction score via domain-adapted SSL model)
  - **NISQA** (Non-Intrusive Speech Quality Assessment for noise/distortions)
  - **Mel-Cepstral Distance (MCD)**: Spectral difference between reference and clone:
    $$\text{MCD} = \frac{10}{\ln 10} \sqrt{2 \sum_{k=1}^K (c_k^{\text{ref}} - c_k^{\text{clone}})^2}$$

---

## 5. Execution Workflow

1. **Prompt Ingestion**: Load $N$ reference speaker utterances.
2. **AudioShield Protection**: Apply `protect_audio` to generate protected prompts.
3. **Automated Synthesis Matrix**:
   - For each target text prompt (10 phonetically balanced sentences), synthesize using:
     - Original prompt audio as reference speaker
     - Protected prompt audio as reference speaker
4. **Automated Evaluation Pipeline**:
   - Run ASR (Whisper) $\rightarrow$ Calculate WER / CER.
   - Run ECAPA-TDNN $\rightarrow$ Calculate Speaker Cosine Similarity.
   - Run UTMOS / MCD $\rightarrow$ Calculate Acoustic Degradation.
5. **Statistical Distribution Reporting**:
   - Report distributions (Mean, Std, Median, IQRs) across all model families without arbitrarily adjusting passing thresholds.
