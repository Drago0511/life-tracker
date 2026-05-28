# Life Tracker — Project Context for Claude Code

## Overview

A personal productivity web app built with Flask 3. Single-user life tracker with tasks, habits, a time-block planner, a calendar, and a weekly AI-powered report. Deployed on Render with PostgreSQL; falls back to a local JSON file (`~/.todo_lists_data.json`) for development.

**GitHub repo:** https://github.com/Drago0511/life-tracker  
**After every change: `git add … && git commit -m "…" && git push origin main`**

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | Flask 3 + Flask-WTF (CSRF) |
| Database | PostgreSQL on Render (psycopg2-binary) |
| Local fallback | JSON file at `~/.todo_lists_data.json` |
| AI | Local `claude` CLI (Claude Haiku) via subprocess |
| Hosting | Render (free tier) — `render.yaml` |
| Server | Gunicorn: `gunicorn src.web:app --bind 0.0.0.0:$PORT` |
| Python | 3.13.0 |

---

## Project Structure

```
/
├── src/
│   ├── web.py          — Flask app, all routes, Jinja filters
│   ├── models.py       — Task, Habit dataclasses + streak logic
│   ├── storage.py      — PostgreSQL + JSON fallback persistence
│   ├── tasks.py        — Task CRUD + recurring logic
│   ├── habits.py       — Habit CRUD + completion/streak
│   ├── views.py        — View data builders (day/week/month/timeblock/report)
│   ├── learning.py     — Insights, duration prediction, AI subtask suggest
│   ├── ai_client.py    — Claude CLI wrapper (has_ai, ai_complete, ai_json)
│   ├── notifications.py— (leading reminder logic)
│   └── templates/
│       ├── index.html        — Shell: all CSS, topbar, sidebar, modals, JS
│       ├── _tasks.html       — Tasks tab (day/week/month/6m/year views)
│       ├── _calendar.html    — Calendar tab (month/week views)
│       ├── _timeblock.html   — Time Block tab (drag-drop scheduler)
│       ├── _habits.html      — Habits tab (grid cards + streaks)
│       └── _report.html      — Weekly report tab (sparkline + AI insight)
├── tests/
├── requirements.txt
├── render.yaml
└── Procfile
```

---

## CSS Architecture: Two-Zone Variable System

The entire UI is split into two colour zones. **Never mix variables across zones.**

### Dark Zone (sidebar + topbar)
Use `--ink*`, `--b*`, `--s*` variables.

### Light Zone (main content area)
Use `--main-ink*`, `--main-b*`, `--main-s*` variables.

---

## Stone & Moss Forest Floor Colour Palette

Full `:root` variables as of the last theme pass:

```css
:root {
  /* ── Dark zone (sidebar / topbar) ── */
  --bg:    #2C2E2A;   /* deep cool granite — page bg */
  --s1:    #1E2018;   /* deep stone — sidebar/topbar bg */
  --s2:    #222520;   /* cool dark — secondary surfaces */
  --s3:    #2A2E26;   /* raised surface */
  --s4:    #34382E;   /* hover surface */
  --b0:    #141610;   /* darkest border */
  --b1:    #282C22;   /* subtle border */
  --b2:    #6B8C5A;   /* mid moss — active borders/accents */
  --b3:    #A3A882;   /* dry sage — muted borders */
  --ink:   #E8E0D0;   /* warm parchment — primary text */
  --ink2:  #C8C4B4;   /* warm light stone — secondary text */
  --ink3:  #A3A882;   /* dry sage — muted text */
  --ink4:  #7A7D72;   /* cool mid-gray — placeholder/label text */

  /* ── Light zone (main content) ── */
  --main-bg:   #E8E0D0;   /* warm parchment — main area bg */
  --main-s1:   #F2EDE4;   /* lightest surface */
  --main-s2:   #E0D8C8;   /* card/chip bg */
  --main-s3:   #D4CCBC;   /* selected/pressed */
  --main-ink:  #1A1C18;   /* near-black — primary text */
  --main-ink2: #3D5C3A;   /* deep forest moss — body text, emphasis */
  --main-ink3: #6B7A5E;   /* mid stone-green — secondary text */
  --main-ink4: #8A8878;   /* muted stone — captions, labels */
  --main-b:    #C8C4B4;   /* warm light stone — dividers/borders */
  --main-b2:   #A3A882;   /* dry sage — hover borders */

  /* ── Priority (5 levels) ── */
  --critical:  #C0392B;   /* blood orange — critical */
  --important: #C26A3A;   /* warm sienna — important */
  --hi:        #C4806A;   /* muted coral — high */
  --md:        #C49A2A;   /* harvest — medium */
  --lo:        #6B8FA3;   /* dusty blue — low */
  --critical-bg: rgba(192,57,43,.12);
  --important-bg:rgba(194,106,58,.12);
  --hi-bg:     rgba(196,128,106,.12);
  --md-bg:     rgba(196,154,42,.12);
  --lo-bg:     rgba(107,143,163,.12);
  --sage-bg:   rgba(107,140,90,.12);

  /* ── Accents ── */
  --cream:     #E8E0D0;   /* parchment */
  --gold:      #8B7D3A;   /* amber moss — UI accent (reopen, goal badges) */
  --violet:    #5A8FA3;   /* steel blue — AI feature accent */
  --sage:      #6B8C5A;   /* mid moss */
  --terracotta:#C4704A;   /* habit terracotta backward compat */
  --glow:      rgba(107,140,90,.22);
  --glow2:     rgba(107,140,90,.1);
  --gold-bg:   rgba(139,125,58,.12);
  --vio-bg:    rgba(90,143,163,.12);
}
```

### Hardcoded rgba → variable mapping
When you see hardcoded rgba values in CSS they follow these patterns:
- Sage/moss: `rgba(107,140,90,…)` — maps to `--sage` / `--glow`
- Critical: `rgba(192,57,43,…)` — maps to `--critical`
- Important: `rgba(194,106,58,…)` — maps to `--important`
- High (muted coral): `rgba(196,128,106,…)` — maps to `--hi`
- Medium (harvest): `rgba(196,154,42,…)` — maps to `--md`
- Low (dusty blue): `rgba(107,143,163,…)` — maps to `--lo`
- Terracotta (habit accent): `rgba(196,112,74,…)` — maps to `--terracotta`
- Gold accent: `rgba(139,125,58,…)` — maps to `--gold` / `--gold-bg`

### Key surface rgba values
- Sidebar bg gradient: `rgba(30,32,24,0.95)` → `rgba(34,37,32,0.97)` (s1 → s2)
- Topbar glassmorphism: `rgba(30,32,24,0.94)`
- Modal backdrop: `rgba(20,22,16,.75)`
- Modal card: `rgba(232,224,208,0.82)` with border `rgba(242,237,228,0.40)`
- Habit card: `rgba(242,237,228,0.85)`

---

## Typography

```
Font serif:  'Cormorant Garamond' (weights 400/500/600/700, italic variants)
Font sans:   'DM Sans' (weights 300/400/500, opsz 9..40)
```

**Usage rules:**
- Serif: app name, group headers, modal titles, motivational lines, empty state messages, habit titles, report period label, section labels
- Sans-serif: everything else (body, labels, inputs, buttons, meta)

**Type scale (CSS):**
- `.sb-lbl` headers: 13px, 700, letter-spacing .15em, uppercase, serif
- `.p-title` pinned tasks: 15px
- `.t-title` task rows: 14px (font-weight by priority: critical=700, important=600, high=500, medium=400, low=300)
- `.group-hd-txt`: 11px, 700, letter-spacing .20em, uppercase, serif
- `.empty-msg`: 17px, 600, serif
- `.empty-sub`: 12px
- `.modal-title`: 16px, 700, serif
- `.motivational-line`: 16px, italic, serif

---

## Spacing Scale

4 / 8 / 12 / 16 / 20 / 24 / 32 / 48px — stick to this. No arbitrary values.

---

## Motion & Animation Standards

All easing curves:
```css
--spring:   cubic-bezier(.34,1.56,.64,1)   /* bouncy, for card lifts / scale pops */
--ease:     cubic-bezier(.4,0,.2,1)         /* standard material ease */
--ease-out: cubic-bezier(0,0,.2,1)          /* decelerating entries */
```

| Element | Spec |
|---|---|
| Task row entrance | `fade-up 250ms ease-out`, stagger `idx × 60ms`, from `translateY(8px)` |
| Tab transition out | `opacity + translateY(6px)` in `120ms ease`, navigate after `125ms` |
| Tab transition in | `180ms ease-out` from `translateY(6px)` |
| Modal open | `scale(0.94) → scale(1)` in `220ms --spring` |
| Modal close | `.closing` class: `scale(0.94) + opacity 0` in `180ms ease`, remove after `190ms` |
| Task completion | Strikethrough draw `350ms`, pause `250ms`, row exit `300ms ease` (total 900ms) |
| Hover states | `180ms ease` default |
| Habit card hover | `translateY(-3px)` with box-shadow `220ms --spring` |
| Add button magnetic | Tracks cursor within button; max `4px` shift at 12% factor |
| Button press | `scale(.96)` active |
| Celebration ring | `cel-ring 2s ease-out` + `cel-msg-fade 3.5s ease` |

**Scroll:** `scroll-behavior: smooth` on `html, body`.

**Grain overlay:** `opacity: .028` fractalNoise SVG, `180px` tile.

---

## Features Built

### Tasks Tab
- Five time-horizon views: **Day**, **Week**, **Month**, **6 Mo**, **Year**
- Day view groups: Projects & Goals (long-term/yearly scope) → Overdue → Today
- Week view: days + unscheduled; Month view: weeks 1–4; 6Mo: by month; Year: by quarter
- **Five priority levels**: Critical (#C0392B) → Important (#C26A3A) → High (#C4806A) → Medium (#C49A2A) → Low (#6B8FA3)
- Priority-weighted font (critical=700, important=600, high=500, medium=400, low=300) for visual hierarchy
- Section divider between Overdue and Today (`.section-divide`)
- Motivational line ("You are right on track.") when 1–2 active tasks in day view
- Show/hide completed toggle
- Date filter (click calendar day → filters task list to that date)
- Category filter via topbar pill
- Task rows animate in with 60ms stagger
- **12h/24h time toggle** in topbar — persists to localStorage, reformats all displayed times client-side without page reload

### Add Task (Sidebar)
- Required: title, category, priority
- Priority selected via **radio pill widget** showing all 5 levels with their color dots simultaneously
- Progressive disclosure (`⊕ Add details`): scope, duration type, due date+time, estimated minutes, repeat
- Leading reminders (shown only when due date is set): 1w / 3d / 1d / 3h / 1h / 30m / 15m / 5m
- "+ New…" option in category dropdown to add inline
- Magnetic add button

### Edit Modal
- Priority also uses radio pill widget (same 5-level picker, light-zone styled)
- Full task edit: all fields + subtasks
- Subtask list with inline add/remove and checkbox completion
- AI subtask suggestion (`✦ Suggest`) — calls Claude CLI (disabled for quick tasks)
- Subtasks render as progress bar in task row
- Recurring: daily / weekly / monthly — auto-creates next occurrence on complete

### Calendar Tab
- Month view: 42-cell grid, priority dots + task chips, today highlighted
- Week view: 7-column layout with task chips
- Navigation: prev/next month or week
- Click any cell → filters task list to that date
- Priority legend shows all 5 levels with their colors

### Time Block Tab
- Hour slots 6am–midnight (labels have `data-hour` attr for time format JS)
- Drag-and-drop: unscheduled chips → time slots (updates `due_datetime`)
- AI Schedule Suggest (`✦ AI Suggest`) — overlays reasoning tips on slots
- Summary panel: counts scheduled vs unscheduled
- Empty state: "Your time, unwritten."

### Habits Tab
- Page header: "Your Rituals" in Cormorant Garamond
- Grid of cards (`auto-fit`, min 220px — collapses empty tracks, no desert effect)
- Card structure: 8px color accent bar → title → body (left/right split) → footer buttons
  - Left half: streak number as centerpiece (48px Cormorant Garamond), "days" label, "Best: N" in dry sage, frequency + category pills
  - Right half: 7-day dot tracker (12px circles in `repeat(4,1fr)` grid — 2 rows of 4+3), day labels (Mon–Sun) in 9px DM Sans
  - Completion state: 15% warm tint of habit color, inner border ring, streak number glows with per-color shadow
- Completion toggle (✓ button) — animated pop on check, uncomplete on re-press
- Streak rules: daily=each day; weekly=one per Mon–Sun; flexible=5× per Mon–Sun week
- Three frequencies: Daily, Weekly, 5× per week (flexible)
- 12 accent colors: forest, terracotta, steel, amber, softviolet, dustyrose, sienna, slate, teal, warmcream, charcoal, plum (displayed as 6×2 grid of 24px circles in picker)
- Old color values (sage, sky, gold, violet) remain valid in stored data; new picker shows 12-color palette
- Add habit: expandable section below cards (dashed border trigger "+ Add a new habit" in Cormorant Garamond)
- Edit habit modal
- Sidebar stat panel: total habits count, done today fraction (e.g. 1/3), longest active streak with 🔥, best overall streak
- Empty state: "Every forest begins with one seed."

### Weekly Report Tab
- Key metrics cards: completed, active, overdue, habits on streak, active goals
- 12-week sparkline (completion trend, bar chart)
- AI Analysis (`✦ AI Insight`) — async via `/ai/weekly-report/start` + poll; renders markdown
- Category breakdown (horizontal bar chart)
- Habit streaks list
- Long-term goals in progress (with subtask ratio)
- Completed tasks this week (strikethrough list)
- Empty state: "Your story starts with the first step."

### Sidebar (all tabs)
- **Focus · Today's Top 3**: top pinned tasks by priority, with due dates, overdue colour
- **Patterns**: peak completion hour, total completed, time accuracy (shown after first completion)
- **Add Task** form (hidden on Habits and Report tabs)
- **Today's Habits** stats panel (shown on Habits tab only)
- **Categories**: list with delete, inline add

### AI Integration
- Backed by local `claude` CLI (no API key needed — uses Claude Code auth)
- Model: Haiku for all AI calls
- `has_ai()` used to conditionally show AI buttons; graceful degradation when CLI absent
- Non-blocking: weekly report uses background thread + `_ai_jobs` dict + polling

### Celebration
- When all pinned tasks are cleared, ripple ring + "All done. Well done." message animates in the sidebar

### Mobile
- Hamburger menu (☰) slides sidebar in as fixed overlay with backdrop
- Modal becomes bottom sheet (`border-radius 18px 18px 0 0`, fixed bottom)
- Task rows reduce padding, cal cells shrink, tb unscheduled panel hidden

---

## Data Models

### Task
```python
id, title, completed, category, due_datetime (ISO str),
priority ("critical"|"important"|"high"|"medium"|"low"), recurring (None|"daily"|"weekly"|"monthly"),
leading_reminders: List[str], description, created_at, scope ("daily"|"weekly"|"monthly"|"yearly"),
duration_type ("quick"|"medium"|"project"), estimated_minutes, actual_minutes,
completed_at, start_date, subtasks: List[{title:str, done:bool}]
```

### Habit
```python
id, title, category, frequency ("daily"|"weekly"|"flexible"),
completions: List["YYYY-MM-DD"],
color ("sage"|"terracotta"|"sky"|"gold"|"violet"|
       "forest"|"steel"|"amber"|"softviolet"|"dustyrose"|
       "sienna"|"slate"|"teal"|"warmcream"|"charcoal"|"plum"),
created_at, archived, best_streak
# Computed properties: completed_today, current_streak, last_7_days
```

### Storage
- PostgreSQL on Render (env: `DATABASE_URL`)
- JSON fallback at `~/.todo_lists_data.json`
- Atomic JSON writes: write to `.tmp`, `fsync`, then `os.replace`

---

## Route Map

```
GET  /                        — main view (tab=tasks|calendar|timeblock|habits|report)
POST /add                     — add task
POST /complete/<id>           — complete task (handles recurring auto-create)
POST /uncomplete/<id>         — reopen task
POST /delete/<id>             — delete task
POST /edit/<id>               — update task
GET  /task/<id>               — task JSON (for modal)
POST /task/<id>/reschedule    — update due_datetime (timeblock drag-drop)
POST /habits/add              — add habit
POST /habits/<id>/complete    — complete habit for today
POST /habits/<id>/uncomplete  — uncomplete habit for today
POST /habits/<id>/edit        — update habit
POST /habits/<id>/delete      — delete habit
POST /categories/add          — add category
POST /categories/delete/<cat> — delete category
GET  /suggest-subtasks               — AI subtask suggestions (query: title, duration_type)
POST /ai/weekly-report/start         — start async AI report generation (returns job_id)
GET  /ai/weekly-report/poll/<job_id> — poll report job status
GET  /ai/schedule-suggest            — AI time-block suggestions
```

---

## CSRF

All POST forms include `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.  
JSON/XHR posts include `'X-CSRFToken': CSRF_TOKEN` header (JS constant set at top of script).

---

## Jinja Filters (registered in web.py)

| Filter | Purpose |
|---|---|
| `fmt_due` | ISO datetime → 12h human label ("Today · 3:30 PM", "May 27 · 9:00 AM"); JS overrides via `data-iso` attr |
| `is_overdue` | ISO datetime → bool (past now) |
| `fmt_minutes` | int minutes → "1h 30m" style |
| `fmt_weekday` | "YYYY-MM-DD" → "Mon 27" |
| `fmt_month_key` | "YYYY-MM" → "May 2026" |
| `fmt_hour` | int hour → "9 AM" / "2 PM" (12h); JS overrides via `data-hour` attr |

---

## Coding Standards

- **Read before editing** — always read a file before making changes
- **No new files unless absolutely necessary** — prefer editing existing files
- **No documentation files** unless explicitly requested
- **Keep files under 500 lines** — web.py is the exception (routes)
- **No comments** in code unless the WHY is genuinely non-obvious
- **No Co-Authored-By** trailers in commits (project setting)
- **Validate at system boundaries only** — trust internal code and Flask guarantees
- **No backwards-compat shims** — if something is removed, remove it completely
- **Spacing scale**: 4/8/12/16/20/24/32/48px — no arbitrary values
- **CSS variables**: never use dark-zone variables (`--ink*`, `--s*`) inside `.main` (light zone), and vice versa
- **Time format**: server renders 12h by default (`fmt_due`, `fmt_hour`); add `data-iso` (ISO datetime) or `data-hour` (int hour) to any new time element so `applyTimeFormat()` can reformat it on toggle
- **Priority**: always use all 5 levels (critical/important/high/medium/low); `--hi` is muted coral #C4806A — do NOT confuse with `--terracotta` #C4704A which is a habit accent
- **Danger/delete states**: use `--critical` / `--critical-bg` (not `--hi`) for delete hovers, overdue text, and error cards
- **All tests must pass** after changes: `python3 -m pytest tests/`
- **Smoke test**: `python3 -c "from src.web import app; c=app.test_client(); [print(t,c.get(f'/?tab={t}').status_code) for t in ['tasks','calendar','timeblock','habits','report']]"`

---

## Running Locally

```bash
pip install -r requirements.txt
python3 src/web.py          # or: flask --app src.web run
# visits http://localhost:5000
```

No `DATABASE_URL` → uses `~/.todo_lists_data.json` automatically.

---

## Deployment (Render)

- Push to `main` → Render auto-deploys
- `render.yaml` provisions a free PostgreSQL database (`life-tracker-db`) and web service
- `SECRET_KEY` env var must be set in Render dashboard for production CSRF security
- Build: `pip install -r requirements.txt`
- Start: `gunicorn src.web:app --bind 0.0.0.0:$PORT`

---

## Design Philosophy

**Forest floor at dusk.** Cool dark stones (sidebar), warm parchment pages (content), rich forest moss accents. Unhurried, grounded, deeply calm. The app should feel like a premium leather notebook, not a dashboard.

**Principles that must not be compromised:**
1. Warm parchment main area — it pops against the dark stone sidebar
2. Priority is communicated through dot colour AND font weight (not just dots)
3. Nothing feels cramped — spacing is generous; breathing room is intentional
4. Animations are purposeful, not decorative — they confirm actions and guide attention
5. AI features degrade gracefully — if `claude` CLI is absent, buttons hide or show a quiet note
6. The serif font (Cormorant Garamond) is reserved for titles, headers, empty states — it signals intention
7. `auto-fit` not `auto-fill` on habit grid — prevents the empty-desert ghost-column problem
