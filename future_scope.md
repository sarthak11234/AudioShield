# AudioShield: Future Scope & Roadmap

As AudioShield successfully transitions from an MVP to a robust V1.0, there are numerous avenues for expansion. The goal is to aggressively adapt to the rapidly evolving Generative AI landscape while opening up new markets beyond independent bedroom producers.

Here is a curated future scope for the AudioShield platform categorized by technological advancement, platform scale, and commercial integrations.

## 1. Advanced Machine Learning & Threat Mitigation
- **Multi-Model Poisoning (Universal adversarial payloads):** Currently tuned for HuBERT/RVC, the noise injection should be generalized or dynamically adjust to poison VITS, So-VITS-SVC, and newer transformer-based audio generation models.
- **Fast Gradient Sign Method (FGSM) Integration:** As noted in the open questions, exploring FGSM or a hybrid FGSM/PGD approach could drastically reduce overhead processing time without sacrificing protection, enabling real-time or near-real-time streaming protection.
- **Psychoacoustic Masking (V2):** Utilizing advanced temporal and spectral frequency masking models that analyze the audio and inject the adversarial permutations purely in the shadows of loud frequencies, achieving a near-perfect Mean Opinion Score (MOS of >4.9).
- **Adversarial Watermarking:** Instead of just destroying the ability to clone, embed a cryptographically secure, imperceptible signature into the audio. If the audio is successfully cloned somehow, this watermark would remain in the output generation, proving the AI stole the artist's IP.

## 2. Platform Scalability & Cloud Architecture
- **Distributed Edge Computing (WASM):** Porting a lighter version of the protective algorithm to WebAssembly, allowing the user's browser to compute the poisoning. This entirely circumvents cloud GPU costs limit and enhances artist privacy.
- **Dynamic Kubernetes Scaling:** Refactoring the current `Celery pool=solo` single GPU constraint to a horizontally scalable Kubernetes cluster on AWS or GCP, spinning up GPU nodes precisely on-demand to handle traffic spikes.
- **Batch Album Processing Interface:** Fulfilling the "Label Intern" persona by enabling bulk zip uploads or integration with multi-track workspaces, distributing track protection asynchronously across multiple worker nodes.

## 3. Commercial & Developer Ecosystem
- **AudioShield Developer API & Webhooks:** Launching a RESTful API allows podcast hosts, indie record labels, distribution platforms (DistroKid, TuneCore), and Patreon-like services to automatically run creator uploads through AudioShield before distribution.
- **Real-Time OBS/Discord Plugin:** For VTubers, voice actors, and Twitch streamers, an AudioShield virtual cable audio interface that locally poisons their mic feed in real-time, preventing livestream viewers from scraping clean audio for models.
- **Subscription Tiers (SaaS):**
  - **Free Tier:** Protects MP3s up to 3 mins, delayed processing queue.
  - **Pro Tier:** WAV/FLAC support, high-priority GPU queue, album batching, up to 100MB limit.
  - **Enterprise Layer:** Dedicated API access, custom SLAs, white-labeled integrations.

## 4. UI/UX Enhancements
- **"Before & After" Validation Player:** Built-in web player allowing the artist to toggle between the original and the `_protected.wav` to personally verify the zero-degradation promise.
- **Push & Email Notifications:** Asynchronous notifications upon Celery task completion, freeing the user from waiting on the frontend progress bar.
- **Workspace/Vault Organization:** Tagging, folders, and improved metadata viewing inside the Vault to track when and what audio was protected.
