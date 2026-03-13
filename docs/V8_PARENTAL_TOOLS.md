# V8 Parental Tools (SRS + Dev Plan)

## 1) Overview
Parental Tools provide stronger control and visibility into a child's browsing behavior. This includes block logs, scheduled rules, reporting, profile switching, and recovery options for PIN reset.

## 2) Scope
- In scope: block log viewer, scheduled rules, email/export reports, PIN recovery, child profiles.
- Out of scope: school-wide admin analytics and community blocklist (Phase 4+).

## 3) User Stories
- As a parent, I can view a detailed log of blocked sites with timestamps and reasons.
- As a parent, I can schedule time windows for strict blocking.
- As a parent, I can export reports weekly or monthly.
- As a parent, I can reset my PIN via a secure recovery method.
- As a parent, I can manage multiple child profiles with separate rules.

## 4) Functional Requirements

### 4.1 Block Log Viewer
- Displays blocked URL, domain, time, risk reason.
- Expandable details per entry.
- Pagination and filter by domain or reason.
- Search field for quick lookup.

### 4.2 Scheduled Rules
- Create rules by day/time:
  - Example: Mon–Fri 07:00–21:00 block social sites.
  - Example: Weekends only moderate rules.
- Priority: allowlist overrides blocklist.

### 4.3 Reports
- One-click export to CSV/JSON.
- Shareable link (local blob or open tab for copy).
- Optional mailto flow for quick email.

### 4.4 Remote PIN Reset
- Recovery phrase (12-word) stored locally and shown once.
- Optional backup email OTP (future).
- Reset clears parental rules unless confirmed.

### 4.5 Multiple Child Profiles
- Each profile has:
  - PIN hash
  - threshold
  - blacklists / whitelists
  - logs
- Profile switcher in parental dashboard.

## 5) Data Model
- parentProfiles[]: { id, name, pinHash, threshold, blacklist, whitelist, logs }
- parentActiveProfile: string
- blockLog[]: { url, domain, ts, reason, riskScore }
- scheduleRules[]: { days[], startTime, endTime, mode, allowlist, blocklist }

## 6) UI Requirements
- Tabbed parental dashboard:
  - Overview (stats + quick actions)
  - Logs
  - Rules
  - Profiles
  - Reports
- PIN protected access.

## 7) Integration Points
- background.js: rule evaluation engine, log writer.
- popup.html/js: parental dashboard UI.
- block.html: show reason + profile badge.

## 8) Dev Plan (Step-by-step)
1. Add block log storage + viewer UI.
2. Implement schedule rule engine in background.js.
3. Add report generator (CSV/JSON).
4. Implement multi-profile store + selector.
5. Build PIN recovery flow.
6. QA: time windows, multi-profile, export integrity.

## 9) Success Criteria
- Logs are reliable and searchable.
- Scheduled rules apply accurately.
- Reports export correctly.
- PIN recovery works without data loss (unless confirmed).
