# V8 Student Tools — Focus Mode (SRS + Dev Plan)

## 1) Overview
Focus Mode is a student-centric study tool that blocks distracting sites, allows study sites, and displays an on-screen timer. Students can choose a countdown (e.g., 30m, 1h, 2h, custom) or a count-up session that ends when they click Finish. Reports summarize study time and sites visited.

## 2) Scope
- In scope: Focus Mode rules, overlay timer, session logs, reports.
- Out of scope (for this phase): parental controls, administrator dashboards, community blocklist sync.

## 3) User Stories
- As a student, I can start Focus Mode for a set duration or open-ended session.
- As a student, I can allow YouTube/Spotify and block social sites while in Focus Mode.
- As a student, I can see a live overlay timer while studying.
- As a student, I can stop Focus Mode by finishing the session.
- As a student, I can view daily/weekly/monthly study summaries.

## 4) Functional Requirements

### 4.1 Session Start
- Student can choose:
  - Countdown: 30m, 1h, 2h, custom minutes.
  - Count-up: starts at 0 and ends on manual Finish.
- System stores `startTime`, `endTime` (if countdown), and `mode`.

### 4.2 Rules During Focus Mode
- Default blocklist (student Focus): Facebook, Instagram, Messenger, TikTok.
- Default allowlist: YouTube, Spotify.
- Student can edit Focus Mode blocklist/allowlist.
- Allowlist overrides blocklist.
- If Focus Mode ends, normal browsing rules resume immediately.

### 4.3 Overlay UI
- Always visible while Focus Mode is active.
- Shows:
  - Remaining time (countdown) or elapsed time (count-up).
  - Current mode label.
  - Finish button (for count-up).
  - Optional Pause (if enabled later).
- Must not be dismissible while Focus Mode is active.

### 4.4 Reports
- Daily, weekly, monthly summaries:
  - Total study time.
  - Number of blocked attempts.
  - Top visited domains during study.
- Session log:
  - Start time, end time, duration.
  - List of top domains visited during Focus Mode.

## 5) Non‑Functional Requirements
- Must work offline without backend dependency.
- Low CPU usage; overlay updates once per second.
- All data stored locally in Chrome storage.

## 6) Data Model (Chrome Storage)
- focusModeEnabled: boolean
- focusModeMode: "countdown" | "open"
- focusModeStartTime: epoch
- focusModeEndTime: epoch | null
- focusModeWhitelist: string[]
- focusModeBlacklist: string[]
- focusModeSessions: array of:
  - startTime, endTime, durationSec
  - blockedAttempts
  - topDomains

## 7) UX / UI Requirements
- Focus Mode entry point in popup menu.
- A dedicated panel for:
  - mode selection
  - timer presets
  - allowlist/blocklist editor
  - session summary
- On-screen overlay design must be simple and unobtrusive.

## 8) Integration Points
- background.js: session lifecycle, allow/block enforcement.
- content.js: overlay injection + timer updates.
- popup.html/js: Focus Mode UI + reports.
- style.css: overlay + panel styles.

## 9) Dev Plan (Step-by-step)
1. Add Focus Mode state manager in background.js.
2. Implement URL allow/block rules during session.
3. Inject overlay timer via content.js.
4. Build Focus Mode UI in popup.html/js.
5. Log sessions + generate daily/weekly/monthly reports.
6. QA: tab refresh, restart Chrome, multi-tab sync.

## 10) Success Criteria
- Focus Mode reliably blocks disallowed sites.
- Overlay stays visible during session.
- Reports summarize time and site usage correctly.
