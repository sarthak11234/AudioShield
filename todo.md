# AudioShield Development Todo

> A systematic breakdown of the AudioShield project into manageable, feature-specific tasks based on PRD.txt, dsign.txt, and techStack.txt.

---

## Phase 1: MVP (Local Prototype) 🎯

### 1. Project Setup & Infrastructure
- [ ] Initialize Next.js project with TypeScript
- [ ] Configure Tailwind CSS with custom color palette (Void Blue, Electric Indigo, Cyan Ray, etc.)
- [ ] Set up project directory structure (frontend, backend, worker)
- [ ] Create `docker-compose.yml` for Redis and PostgreSQL
- [ ] Configure environment variables template (`.env.example`)

### 2. Backend API Foundation (FastAPI)
- [ ] Initialize FastAPI project with proper folder structure
- [ ] Set up SQLAlchemy + PostgreSQL connection
- [ ] Create database models (Task, FileMetadata)
- [ ] Configure Pydantic schemas for validation
- [ ] Implement health check endpoint
- [ ] Set up CORS middleware for frontend communication

### 3. Core ML Worker (Celery + PyTorch)
- [ ] Set up Celery worker with Redis broker
- [ ] Implement audio file loading with Torchaudio
- [ ] Load HuBERT model from Hugging Face Transformers
- [ ] Implement PGD (Projected Gradient Descent) attack logic
- [ ] Create audio chunking system (<15s chunks for 6GB VRAM)
- [ ] Implement chunk stitching with zero-crossing alignment
- [ ] Add basic audio quality preservation

### 4. File Processing Pipeline
- [ ] Implement file upload endpoint (`.wav`, `.mp3`, max 50MB)
- [ ] Generate unique Task ID on upload
- [ ] Create job queueing system (1 active job per GPU limit)
- [ ] Implement file storage with automatic cleanup (1 hour TTL)
- [ ] Build download endpoint for protected files

---

## Phase 2: Web Service (Beta) 🌐

### 5. Frontend - Design System & Layout
- [ ] Install and configure Framer Motion for animations
- [ ] Set up Recharts for dashboard visualizations
- [ ] Add Lucide React icons
- [ ] Create glassmorphism component library (Glass Panel, Surface Materials)
- [ ] Implement dark mode color tokens as CSS variables
- [ ] Build responsive 3-column grid layout (Dashboard structure)

### 6. Frontend - Navigation & Sidebar
- [ ] Create frosted glass sidebar component
- [ ] Implement navigation menu (Overview, My Vault, Protect New, Settings)
- [ ] Design abstract Shield logo with gradient
- [ ] Add collapsed/expanded sidebar toggle
- [ ] Implement mobile-responsive sidebar stacking

### 7. Frontend - Dashboard (Command Center)
- [ ] Build "Security Health" hero widget with donut chart
- [ ] Create catalog security percentage visualization
- [ ] Implement "Recent Activity Cards" component (transaction-style)
- [ ] Build status badges (SECURE/VULNERABLE pills)
- [ ] Create "AI Landscape Monitor" widget with line graph
- [ ] Add "Protect New Track" floating CTA button with glow effect

### 8. Frontend - Upload Flow (The Forge)
- [ ] Build drag-and-drop zone with animated pulsing border
- [ ] Add 3D isometric shield/lock illustration
- [ ] Implement file type validation (WAV/FLAC only)
- [ ] Display privacy micro-copy ("Files deleted after 1 hour")
- [ ] Create "Biometric Scan" processing animation
- [ ] Implement waveform visualization with scanner line
- [ ] Add animated status text ("Analyzing..." → "Generating..." → "Injecting...")
- [ ] Build gradient progress bar

### 9. Frontend - Success State & Download
- [ ] Design "Certificate of Deposit" card component
- [ ] Display protection metadata (Type, Quality, Noise Level)
- [ ] Implement primary download button (Protected Master)
- [ ] Add secondary "View Spectrogram" link
- [ ] Create album art/waveform placeholder

### 10. Real-time Status Updates
- [ ] Implement WebSocket connection for live status
- [ ] Create status state machine (Queued → Processing → Completed)
- [ ] Build real-time progress bar updates
- [ ] Add task polling fallback mechanism

### 11. API Integration (Frontend ↔ Backend)
- [ ] Create API client service layer
- [ ] Implement file upload with progress tracking
- [ ] Build task status polling/WebSocket integration
- [ ] Handle download of protected files
- [ ] Add error handling and retry logic

---

## Phase 3: V1.0 (Public Launch) 🚀

### 12. Audio Quality Enhancement
- [ ] Implement psychoacoustic masking in PGD loop
- [ ] Add perceptual loss function
- [ ] Mask noise under loud frequencies
- [ ] Validate MOS > 4.0 audio quality target
- [ ] Test imperceptibility of adversarial noise

### 13. Batch Processing
- [ ] Extend upload to accept multiple files
- [ ] Build batch job queue management
- [ ] Create album/batch progress tracking UI
- [ ] Implement ZIP download for batch results

### 14. User Accounts & Authentication
- [ ] Implement user registration/login (PostgreSQL)
- [ ] Create protected routes and sessions
- [ ] Build user dashboard with processing history
- [ ] Add "My Vault" library (historical archive)

### 15. The Vault (Library Feature)
- [ ] Design file library grid/list view
- [ ] Implement search and filter functionality
- [ ] Add swipe gestures for mobile (Download/Delete)
- [ ] Create file metadata display

### 16. Notification System
- [ ] Implement "Email me when done" feature
- [ ] Set up email service integration
- [ ] Create notification preferences UI

### 17. Micro-interactions & Polish
- [ ] Add hover effects (scale 1.02, glow intensify)
- [ ] Implement button press feedback (scale 0.98)
- [ ] Replace spinners with "Data Stream" animations
- [ ] Add page transition animations
- [ ] Optimize loading states throughout

### 18. Mobile Responsiveness
- [ ] Test and fix 3-column to vertical stacking
- [ ] Implement sticky FAB button for mobile
- [ ] Add swipe gestures for library management
- [ ] Verify touch targets and spacing

### 19. Performance & Optimization
- [ ] Research FGSM vs PGD speed tradeoffs
- [ ] Optimize inference time (target: <2 min for 3-min song)
- [ ] Implement request rate limiting
- [ ] Add server health monitoring

### 20. Legal & Compliance
- [ ] Add protection disclaimer ("not 100% guaranteed")
- [ ] Create privacy policy page
- [ ] Implement terms of service
- [ ] Add data handling transparency

---

## Testing & QA Checklist

- [ ] Unit tests for ML pipeline (chunking, PGD, stitching)
- [ ] API endpoint integration tests
- [ ] Frontend component tests
- [ ] End-to-end upload → process → download flow
- [ ] VRAM stress testing (prevent OOM crashes)
- [ ] Audio quality validation (before/after comparison)
- [ ] Cross-browser compatibility testing
- [ ] Mobile device testing

---

## Success Metrics to Validate

| Metric | Target |
|--------|--------|
| Processing Success Rate | >95% |
| Inference Time (3-min song) | <2 minutes |
| Audio Quality (MOS) | >4.0 |
| AI Cloning Disruption | >80% |

---

*Last Updated: January 23, 2026*
