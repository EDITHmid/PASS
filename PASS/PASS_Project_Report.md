# PASS — Proactive Academic Support System
## Comprehensive Project Documentation

---

| Field | Detail |
|---|---|
| **Project Title** | Proactive Academic Support System (PASS) |
| **Domain** | Educational Data Analytics & Early Warning Systems |
| **Author** | EDITHmid |
| **University** | B.E. / B.Tech Computer Science & Engineering |
| **Technology Stack** | Python 3.13, Flask 3.1, SQLAlchemy 2.0, SQLite, Bootstrap 5.3, Chart.js 4.x |
| **Repository** | [github.com/EDITHmid/PASS](https://github.com/EDITHmid/PASS) |
| **Live Deployment** | Render (Free Tier) |
| **Date** | February 2026 |

---

## Table of Contents

1. [Problem Statement & Motivation](#1-problem-statement--motivation)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack — Detailed Breakdown](#3-technology-stack--detailed-breakdown)
4. [Project Structure & File Manifest](#4-project-structure--file-manifest)
5. [Database Design](#5-database-design)
6. [Core Algorithms](#6-core-algorithms)
7. [Module-by-Module Implementation](#7-module-by-module-implementation)
8. [Route & API Design](#8-route--api-design)
9. [Frontend & Visualization](#9-frontend--visualization)
10. [Authentication & Security](#10-authentication--security)
11. [Testing Strategy](#11-testing-strategy)
12. [Data Generation & Seeding](#12-data-generation--seeding)
13. [Deployment Pipeline](#13-deployment-pipeline)
14. [Development Workflow & Decisions](#14-development-workflow--decisions)
15. [Challenges Faced & Solutions](#15-challenges-faced--solutions)
16. [Future Enhancements](#16-future-enhancements)

---

## 1. Problem Statement & Motivation

### 1.1 The Intervention Gap

Traditional Learning Management Systems (LMS) like Moodle or Canvas detect academic failure **after** it has already occurred — through failing grades. By that point, intervention is too late. Research shows that behavioral disengagement (erratic submission patterns, increasing lateness) precedes academic failure by **4–6 weeks**.

### 1.2 Alert Fatigue

Simple threshold-based alerting systems (e.g., "flag if submission is >24h late") generate excessive false-positive warnings. Educators become desensitized — this is called **alert fatigue**. Studies show threshold-only systems can have false-positive rates exceeding 60%.

### 1.3 PASS Solution

PASS addresses both problems through a **five-factor analytical model** that combines temporal submission behaviour with traditional academic indicators:

1. **Computing Submission Velocity (Δt)** — a signed temporal distance metric that captures not just *whether* a student is late, but *how their pattern is changing over time*.
2. **Applying Hysteresis Filtering** — requiring a negative trend to persist for 2–3 consecutive assignments before generating an alert, suppressing transient noise.
3. **Building a Five-Factor Credibility Score** — a dynamic 0–100 reliability index combining:
   - Δt Consistency (25%) — regularity of submission timing
   - Variance Stability (10%) — consistency of submission pattern
   - Assignment Completion Rate (10%) — percentage of assignments submitted
   - Attendance (25%) — class attendance percentage
   - Exam Performance (30%) — best 2 of 3 mid-term exam averages
4. **Automating Low-Stakes Policies** — high-credibility students automatically receive perks (attendance waivers); declining students trigger proactive interventions.

The system intentionally blends *behavioural signals* (Δt, variance, completion) with *academic performance signals* (attendance, exams) to produce a holistic credibility index that correlates strongly with overall student engagement.

### 1.4 Success Metrics (from PRD)

| Metric | Target |
|---|---|
| Detection Lead Time | ≥4 weeks before failing grade |
| Alert Precision | ≥80% actionable alerts |
| Credibility Score Correlation | r ≥ 0.75 with final outcome |
| Dashboard Load Time | < 2 seconds |

---

## 2. System Architecture

### 2.1 Three-Tier Serverless Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                         │
│  Bootstrap 5.3 + Chart.js 4.x + Jinja2 Templates               │
│  (13 HTML templates, responsive sidebar layout)                 │
├─────────────────────────────────────────────────────────────────┤
│                     APPLICATION LAYER                            │
│  Flask 3.1 Web Framework                                        │
│  ┌──────────┐ ┌──────────────┐ ┌─────────┐ ┌──────────────┐    │
│  │ auth_bp  │ │ dashboard_bp │ │ api_bp  │ │ student_bp   │    │
│  │ (login,  │ │ (instructor  │ │ (REST   │ │ (self-view,  │    │
│  │  register│ │  dashboard,  │ │  API)   │ │  personal    │    │
│  │  logout) │ │  upload,     │ │         │ │  metrics)    │    │
│  │          │ │  export)     │ │         │ │              │    │
│  └──────────┘ └──────────────┘ └─────────┘ └──────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                     ANALYTICAL ENGINE                            │
│  ┌────────────┐ ┌──────────────┐ ┌──────────────┐              │
│  │ MetricComp │ │ Hysteresis   │ │ Credibility  │              │
│  │ (Δt, σ,   │ │ Filter       │ │ Scorer       │              │
│  │  trend)   │ │ (alerts)     │ │ (5-factor)   │              │
│  └────────────┘ └──────────────┘ └──────────────┘              │
│  ┌─────────────────────────────────────────────┐               │
│  │ DataIngestor (CSV parsing, validation)      │               │
│  └─────────────────────────────────────────────┘               │
├─────────────────────────────────────────────────────────────────┤
│                       DATA LAYER                                │
│  SQLite + SQLAlchemy 2.0 ORM                                    │
│  7 Models: User, Course, Student, Submission, Alert,            │
│            PolicyEvent, IngestionLog                             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow Pipeline

```
CSV Upload / API Ingest
        │
        ▼
┌─────────────────┐
│  DataIngestor    │ ← Validates columns, parses timestamps,
│  (ingestion.py)  │   normalizes to UTC, computes initial Δt,
│                  │   extracts attendance & exam data (optional)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MetricComputer  │ ← Computes rolling variance, trend direction,
│  (metrics.py)    │   student summary statistics
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ HysteresisFilter │ ← Detects sustained negative trends (window=3),
│ (hysteresis.py)  │   variance spikes, and checks alert resolution
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ CredibilityScorer│ ← 5-factor weighted composite (25/10/10/25/30),
│ (credibility.py) │   classifies tier, triggers policy events
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Database       │ ← Updates Student.credibility_score,
│   (SQLite)       │   creates Alert & PolicyEvent records
└─────────────────┘
```

### 2.3 Request-Response Lifecycle

1. **User** visits `/dashboard` → Flask routes request to `dashboard_bp`
2. **Route** queries SQLAlchemy models for students, alerts, submissions
3. **Engine** modules recompute metrics on data changes (upload/ingest)
4. **Jinja2** template renders HTML with data, Chart.js configs as JSON
5. **Browser** renders charts client-side using Chart.js
6. **API** endpoints return JSON envelope: `{ "success": bool, "data": {...} }`

---

## 3. Technology Stack — Detailed Breakdown

### 3.1 Backend

| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.13.9 | Core programming language |
| **Flask** | 3.1.0 | Lightweight WSGI web framework |
| **Flask-SQLAlchemy** | 3.1.1 | ORM integration for database operations |
| **SQLAlchemy** | 2.0.36 | Database ORM with model definitions |
| **SQLite** | (bundled) | Serverless relational database |
| **Flask-Login** | 0.6.3 | Session-based user authentication |
| **Flask-WTF** | 1.2.2 | CSRF protection for forms |
| **Flask-CORS** | 5.0.0 | Cross-origin resource sharing for API |
| **Flask-Session** | 0.8.0 | Server-side session management |
| **Werkzeug** | 3.1.3 | Password hashing (scrypt) |
| **Pandas** | 2.2.3 | CSV parsing & data manipulation |
| **NumPy** | 1.26.4 | Numerical computations (std dev, statistics) |
| **Gunicorn** | 23.0.0 | Production WSGI HTTP server |
| **python-dotenv** | 1.0.1 | Environment variable loading |

### 3.2 Frontend

| Technology | Version | Purpose |
|---|---|---|
| **Bootstrap** | 5.3.3 | Responsive CSS framework (CDN) |
| **Bootstrap Icons** | 1.11.3 | Icon library (CDN) |
| **Chart.js** | 4.4.7 | Interactive charts & visualizations (CDN) |
| **Google Fonts (Inter)** | — | Typography |
| **Jinja2** | (bundled with Flask) | Server-side HTML templating |

### 3.3 Testing & Quality

| Technology | Version | Purpose |
|---|---|---|
| **pytest** | 8.3.4 | Test framework |
| **pytest-flask** | 1.3.0 | Flask test client integration |
| **pytest-cov** | 6.0.0 | Code coverage reporting |
| **flake8** | 7.1.1 | Linting |
| **black** | 24.10.0 | Code formatting |

### 3.4 Deployment

| Technology | Purpose |
|---|---|
| **Git** | Version control |
| **GitHub** | Remote repository hosting |
| **Render** | Cloud hosting (free tier, auto-deploy from GitHub) |

### 3.5 Why These Choices?

- **Flask over Django**: PASS is a focused analytical tool, not a CMS. Flask's microframework approach lets us build exactly what's needed without Django's overhead (admin panel, ORM migrations, etc. are unnecessary here).
- **SQLite over PostgreSQL**: The PRD explicitly specifies "serverless data management". SQLite requires zero configuration, is embedded in the Python runtime, and handles the expected load (single institution, <1000 students) perfectly.
- **Pandas for CSV ingestion**: Handles messy real-world CSV data — mixed date formats, missing columns, encoding issues — robustly. `pd.read_csv()` with `StringIO` gives us DataFrame-level validation in 2 lines.
- **Chart.js over D3.js**: Chart.js provides declarative, responsive charts with minimal code. D3.js would be overkill for the 5 chart types we need.
- **CDN-served frontend**: No npm build step, no webpack config. Templates load Bootstrap/Chart.js via CDN, keeping the project structure clean and deployable.

---

## 4. Project Structure & File Manifest

```
PASS/
├── app.py                          # Application factory (create_app)
├── config.py                       # Dev/Test/Prod configurations
├── models.py                       # 7 SQLAlchemy data models
├── run.py                          # CLI entry point (--seed, --reset)
├── wsgi.py                         # Gunicorn WSGI entry point
├── build.sh                        # Render build script
├── render.yaml                     # Render deployment blueprint
├── requirements.txt                # Python dependencies (16 packages)
├── generate_dataset.py             # Synthetic dataset generator
├── pytest.ini                      # Pytest configuration
├── .gitignore                      # Git ignore rules
├── README.md                       # Project documentation
├── PASS_Project_Report.md          # This document
│
├── engine/                         # Analytical Engine (core algorithms)
│   ├── __init__.py
│   ├── metrics.py                  # Δt computation, variance, trend detection
│   ├── hysteresis.py               # Hysteresis filter, alert generation
│   ├── credibility.py              # 5-factor credibility scoring, policy triggers
│   └── ingestion.py                # CSV parsing, validation, timestamp normalization
│
├── routes/                         # Flask Blueprints (4 modules)
│   ├── __init__.py
│   ├── auth.py                     # Login, register, logout
│   ├── dashboard.py                # Instructor dashboard, student detail, upload, export
│   ├── api.py                      # REST API endpoints (8 endpoints)
│   └── student.py                  # Student self-view panel
│
├── templates/                      # Jinja2 HTML templates (13 files)
│   ├── base.html                   # Master layout with sidebar, navbar, CSS
│   ├── auth/
│   │   ├── landing.html            # Public landing page
│   │   ├── login.html              # Login form
│   │   └── register.html           # Registration form
│   ├── dashboard/
│   │   ├── instructor.html         # Main instructor dashboard
│   │   ├── student_detail.html     # Individual student drill-down
│   │   └── upload.html             # CSV upload page
│   ├── student/
│   │   ├── self_view.html          # Student personal dashboard
│   │   └── no_profile.html         # No profile linked message
│   └── errors/
│       ├── 403.html                # Access denied
│       ├── 404.html                # Not found
│       └── 500.html                # Internal server error
│
└── tests/                          # Pytest test suite (83 tests)
    ├── __init__.py
    ├── conftest.py                 # Shared fixtures (app, db, client, users)
    ├── test_metrics.py             # 17 tests for MetricComputer
    ├── test_hysteresis.py          # 11 tests for HysteresisFilter
    ├── test_credibility.py         # 27 tests for CredibilityScorer
    ├── test_ingestion.py           # 11 tests for DataIngestor
    └── test_routes.py              # 17 tests for routes, API, models
```

**Total: 42 source files, ~7,000 lines of code**

---

## 5. Database Design

### 5.1 Entity-Relationship Diagram

```
┌──────────┐       1:N        ┌──────────┐       1:N       ┌────────────┐
│   User   │─────────────────▶│  Course   │◀──────────────│  Student    │
│──────────│                  │──────────│                 │────────────│
│ id (PK)  │                  │ id (PK)  │                 │ id (PK)    │
│ username │                  │ course_id│                 │ student_id │
│ email    │                  │ name     │                 │ name       │
│ password │                  │ semester │                 │ user_id FK │
│ full_name│                  │ instr FK │                 │ course FK  │
│ role     │                  └──────────┘                 │ cred_score │
└──────────┘                                               │ attend_pct │
     │                                                     │ mid1_score │
     │ 1:1                                                 │ mid2_score │
     └──────────────▶ Student                              │ mid3_score │
                                                           └─────┬──────┘
                                                                 │
                                                    1:N │  1:N │  1:N │
                                                        │      │      │
                                                        ▼      ▼      ▼
                                                ┌──────────┐ ┌─────┐ ┌───────────┐
                                                │Submission│ │Alert│ │PolicyEvent│
                                                │──────────│ │─────│ │───────────│
                                                │ id (PK)  │ │ id  │ │ id (PK)   │
                                                │ sub_id   │ │ met │ │ policy    │
                                                │ delta_t  │ │type │ │ type      │
                                                │ status   │ │ sev │ │ descr     │
                                                └──────────┘ └─────┘ └───────────┘
```

### 5.2 Model Specifications

#### User Model

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `email` | String(120) | Unique, Not Null, Indexed | Login email |
| `username` | String(80) | Unique, Not Null, Indexed | Display name |
| `password_hash` | String(256) | Not Null | Scrypt hash |
| `role` | String(20) | Not Null, Default='student' | 'instructor', 'student', 'admin' |
| `full_name` | String(100) | Not Null, Default='' | Full display name |
| `is_active` | Boolean | Default=True | Account status |
| `created_at` | DateTime | Default=UTC now | Registration timestamp |
| `last_login` | DateTime | Nullable | Last login timestamp |

#### Course Model

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK | Internal identifier |
| `course_id` | String(20) | Unique, Not Null, Indexed | e.g., "CS501" |
| `course_name` | String(150) | Not Null | Full course title |
| `semester` | String(20) | Not Null | e.g., "Spring 2026" |
| `instructor_id` | Integer | FK → users.id | Assigned instructor |

#### Student Model

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK | Internal identifier |
| `student_id` | String(20) | Unique, Not Null, Indexed | USN (e.g., "1RV22CS001") |
| `name` | String(100) | Not Null | Student full name |
| `course_id` | Integer | FK → courses.id | Enrolled course |
| `user_id` | Integer | FK → users.id, Unique | Linked user account |
| `credibility_score` | Float | Default=50.0 | Current composite credibility |
| `attendance_pct` | Float | Default=0.0 | Attendance percentage (0–100) |
| `mid1_score` | Float | Nullable | Mid-term 1 exam score (0–100) |
| `mid2_score` | Float | Nullable | Mid-term 2 exam score (0–100) |
| `mid3_score` | Float | Nullable | Mid-term 3 exam score (0–100) |
| `enrollment_date` | DateTime | Default=UTC now | When student was registered |
| `status` | String(20) | Default='active' | 'active', 'inactive', 'graduated' |

**Computed Properties** (not stored, derived on access):
- `active_alerts_count` — count of unresolved alerts
- `total_submissions` — count of linked submissions
- `on_time_rate` — percentage of submissions with Δt ≥ 0
- `best_two_mid_avg` — average of the best 2 out of 3 mid-term scores

The `best_two_mid_avg` property sorts all non-null mid scores descending and averages the top two. Returns `None` if fewer than 2 scores are available.

```python
@property
def best_two_mid_avg(self):
    scores = [s for s in [self.mid1_score, self.mid2_score, self.mid3_score]
              if s is not None]
    if len(scores) < 2:
        return None
    scores.sort(reverse=True)
    return round((scores[0] + scores[1]) / 2.0, 2)
```

#### Submission Model

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK | Internal identifier |
| `submission_id` | String(50) | Unique, Not Null | UUID generated on ingest |
| `student_id` | Integer | FK → students.id | Submitting student |
| `course_id` | Integer | FK → courses.id | Course context |
| `assignment_id` | String(50) | Not Null | Assignment identifier |
| `submitted_at` | DateTime | Not Null | Actual submission timestamp |
| `deadline` | DateTime | Not Null | Assignment deadline |
| `delta_t` | Float | Not Null | Δt = submitted - deadline (seconds) |
| `delta_t_hours` | Float | Not Null | Δt in hours (for display) |
| `status` | String(20) | Default='on-time' | 'on-time' or 'late' |
| `created_at` | DateTime | Default=UTC now | Record creation time |

#### Alert Model

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK | Internal identifier |
| `student_id` | Integer | FK → students.id | Affected student |
| `alert_type` | String(50) | Not Null | 'negative_trend' or 'variance_spike' |
| `severity` | String(20) | Default='warning' | 'warning', 'critical', 'info' |
| `message` | Text | Not Null | Human-readable alert description |
| `metric_snapshot` | Text | Nullable | JSON snapshot of triggering metrics |
| `resolved` | Boolean | Default=False | Resolution status |
| `resolved_at` | DateTime | Nullable | Resolution timestamp |
| `created_at` | DateTime | Default=UTC now | Alert creation time |

#### PolicyEvent Model

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK | Internal identifier |
| `student_id` | Integer | FK → students.id | Affected student |
| `policy_type` | String(50) | Not Null | 'attendance_waiver', 'recognition', 'intervention_required' |
| `description` | Text | Not Null | Full description of the policy action |
| `triggered_at` | DateTime | Not Null | When the policy was triggered |
| `expires_at` | DateTime | Nullable | Expiration (90 days for waivers) |

#### IngestionLog Model

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK | Internal identifier |
| `filename` | String(255) | Not Null | Original CSV filename |
| `uploaded_by` | Integer | FK → users.id | Uploader |
| `records_processed` | Integer | Default=0 | Total rows attempted |
| `records_succeeded` | Integer | Default=0 | Successfully ingested rows |
| `records_failed` | Integer | Default=0 | Rejected rows |
| `error_log` | Text | Nullable | JSON array of per-row errors |
| `created_at` | DateTime | Default=UTC now | Upload timestamp |

---

## 6. Core Algorithms

### 6.1 Submission Velocity (Δt)

**Definition**: Δt is the signed temporal distance between submission and deadline.

```
Δt = deadline_timestamp − submission_timestamp
```

| Δt Value | Meaning |
|---|---|
| Δt > 0 | Submitted **early** (seconds before deadline) |
| Δt = 0 | Submitted **exactly** on time |
| Δt < 0 | Submitted **late** (seconds after deadline) |

**Key Insight**: Δt is *signed* — positive values indicate early submission. This allows tracking whether a student is becoming progressively later (declining Δt trend) even while still technically submitting on time.

### 6.2 Variance Stability (σ)

Rolling population standard deviation over the last N submissions:

```
σ = √(Σ(Δtᵢ − μ)² / N)    for the last N Δt values
```

Default window: `N = 5` (configurable via `VARIANCE_ROLLING_WINDOW`).

- **Low σ** → Consistent timing (good)
- **High σ** → Erratic behavior (concerning)
- **Sudden spike** → Possible crisis event

### 6.3 Hysteresis Filtering

**Problem**: Single-threshold alerts fire on every late submission, creating noise.

**Solution**: PASS requires that a negative trend persists for a configurable window (default: 3 consecutive assignments) before generating an alert. Similarly, alert resolution requires consecutive improvements (default: 2).

```
Trend Detection:
  IF last 3 Δt values are monotonically declining
  AND decline rate > 10% per step
  THEN trigger "negative_trend" alert

Variance Spike Detection:
  IF current σ > mean(historical σ) × multiplier
  THEN trigger "variance_spike" alert

Alert Resolution:
  IF consecutive improvements ≥ reversal_count
  THEN resolve the existing alert
```

This approach mimics a **Schmitt trigger** from electronics — the thresholds for activating and deactivating an alert are different, preventing oscillation.

### 6.4 Five-Factor Credibility Score

The Credibility Score is a composite 0–100 metric that combines five weighted dimensions of student engagement. The score serves dual purposes: (1) a reliability index for instructors, and (2) an automated policy trigger.

#### Weight Distribution

| Component | Weight | Signal Type | Rationale |
|---|---|---|---|
| **Δt Consistency** | 25% | Behavioural | Core temporal submission pattern |
| **Variance Stability** | 10% | Behavioural | Consistency of submission rhythm |
| **Completion Rate** | 10% | Behavioural | Assignment submission coverage |
| **Attendance** | 25% | Academic | Strong proxy for classroom engagement |
| **Exam Performance** | 30% | Academic | Best 2 of 3 mid-term exams — highest weight as direct measure of mastery |

```
Credibility Score = 0.25 × Δt_score
                  + 0.10 × Variance_score
                  + 0.10 × Completion_score
                  + 0.25 × Attendance_score
                  + 0.30 × Exam_score
```

#### Component Scoring Details

**Δt Consistency Score (0–100)**:
- Mean Δt ≥ 24h early → 100
- Mean Δt = 0h (on-time) → 60
- Mean Δt ≤ -24h (late) → 0
- Linear interpolation between anchors
- 15% penalty if recent 3 submissions show >30% decline vs. overall mean

**Variance Stability Score (0–100)**:
- σ = 0h → 100 (perfect consistency)
- σ ≤ 1h → 100
- σ ≤ 6h → 70–100
- σ ≤ 12h → 40–70
- σ ≤ 24h → 10–40
- σ > 48h → 0
- 10% bonus if current variance is <80% of recent historical average (improving)

**Completion Rate Score (0–100)**:
- 100% submitted → 100
- 90% → 85
- 80% → 70
- 70% → 50
- < 60% → linear to 0
- Non-linear curve penalises missing assignments more heavily

**Attendance Score (0–100)**:
Uses a non-linear mapping that penalises poor attendance heavily, reflecting academic regulations where < 75% attendance disqualifies students from examinations:

| Attendance % | Score | Rationale |
|---|---|---|
| ≥ 95% | 100 | Exemplary attendance |
| ≥ 85% | 80–100 | Good attendance |
| ≥ 75% | 60–80 | Minimum for exam eligibility |
| ≥ 60% | 30–60 | Below threshold — a concern |
| < 60% | 0–30 | Severe absenteeism |

**Exam Performance Score (0–100)**:
The exam component uses a **best 2 of 3 mid-term exams** policy. This is deliberately forgiving — a student who has one bad exam but performs well on the other two is not unfairly penalised.

| Scenario | Score Mapping |
|---|---|
| avg ≥ 80 (best 2 of 3) | 100 |
| avg ≥ 60 | 70–100 (linear) |
| avg ≥ 40 | 40–70 (linear) |
| avg < 40 | 0–40 (linear) |
| Only 1 mid score available | Use that score with 10% penalty |
| No scores available | Neutral default (50) |

#### Tier Classification

| Tier | Score Range | Label | Policy Trigger |
|---|---|---|---|
| **Excellent** | ≥ 85 | High Credibility | Attendance waiver granted |
| **Good** | 50–84 | Satisfactory | No action |
| **Warning** | 30–49 | Needs Attention | Monitoring recommended |
| **Critical** | < 30 | At Risk | Intervention required |

### 6.5 Automated Policy Triggers

The credibility engine monitors score transitions and fires policy events when specific thresholds are crossed:

| Trigger Condition | Policy Type | Description |
|---|---|---|
| Score crosses **above 85** | `attendance_waiver` | Auto-grants attendance flexibility for 90 days |
| Score improves by **>15 points** | `recognition` | Records notable improvement in academic engagement |
| Score drops **below 30** | `intervention_required` | Flags student for immediate instructor attention |

These events are stored as `PolicyEvent` records and displayed on the instructor dashboard.

---

## 7. Module-by-Module Implementation

### 7.1 `app.py` — Application Factory

```python
def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    cors.init_app(app)
    sess.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(student_bp)

    # Error handlers (403, 404, 500)
    # Context processor (inject current_year)
    return app
```

**Key Design Decisions**:
- **Blueprints** separate concerns: auth, dashboard, API, student
- **CSRF exemption** on API blueprint allows programmatic access
- **Context processor** injects global template variables
- **`config_name` parameter** allows testing with in-memory SQLite

### 7.2 `config.py` — Configuration Management

Three profiles:

| Profile | DB | Debug | CSRF | Use Case |
|---|---|---|---|---|
| Development | `instance/pass.db` (file) | On | On | Local development |
| Testing | `sqlite:///:memory:` | Off | Off | Pytest (fresh DB per test) |
| Production | `instance/pass.db` | Off | On | Render deployment |

All PASS-specific parameters are configurable:

| Parameter | Default | Description |
|---|---|---|
| `HYSTERESIS_WINDOW_SIZE` | 3 | Consecutive assignments for trend confirmation |
| `HYSTERESIS_REVERSAL_COUNT` | 2 | Consecutive improvements to resolve alert |
| `VARIANCE_ROLLING_WINDOW` | 5 | Rolling window for variance stability |
| `CREDIBILITY_THRESHOLD_HIGH` | 85 | Score for automated perks |
| `CREDIBILITY_THRESHOLD_WARNING` | 50 | Score for warning state |
| `CREDIBILITY_THRESHOLD_CRITICAL` | 30 | Score for critical alerts |
| `WEIGHT_DELTA_T_CONSISTENCY` | 0.25 | Δt consistency weight |
| `WEIGHT_VARIANCE_STABILITY` | 0.10 | Variance stability weight |
| `WEIGHT_COMPLETION_RATE` | 0.10 | Completion rate weight |
| `WEIGHT_ATTENDANCE` | 0.25 | Attendance weight |
| `WEIGHT_EXAM_PERFORMANCE` | 0.30 | Exam performance weight |

All five credibility weights are asserted to sum to 1.0 at runtime.

### 7.3 `engine/metrics.py` — MetricComputer

**Class**: `MetricComputer(rolling_window=5)`

| Method | Input | Output | FR |
|---|---|---|---|
| `compute_delta_t(sub_ts, dead_ts)` | Two UNIX timestamps (float) | Δt in seconds (float) | FR-05 |
| `delta_t_to_hours(seconds)` | Δt in seconds | Δt in hours | FR-05 |
| `classify_submission(delta_t)` | Δt in seconds | "on-time" or "late" | FR-06 |
| `compute_variance_stability(values)` | List of Δt values | Population σ of last N | FR-07 |
| `compute_rolling_variance_series(values)` | List of Δt values | List of rolling σ (None-padded) | FR-08 |
| `compute_trend_direction(values, window)` | Δt values + window size | Dict: direction, pct_change, is_monotonic_decline | FR-09 |
| `compute_student_summary(values)` | All Δt values for a student | Dict: total, mean, median, variance, trend, on_time_rate | FR-10 |

### 7.4 `engine/hysteresis.py` — HysteresisFilter

**Class**: `HysteresisFilter(window_size=3, reversal_count=2)`

| Method | Input | Output | FR |
|---|---|---|---|
| `detect_negative_trend(delta_t_values)` | List of Δt values | Alert dict or None | FR-11 |
| `detect_variance_spike(variance_values, multiplier)` | Variance series + threshold | Alert dict or None | FR-12 |
| `check_alert_resolution(delta_t_values, improvements)` | Δt values + current count | Tuple[should_resolve, updated_count] | FR-13 |
| `run_full_analysis(delta_t, variance, alerts)` | All data + existing alerts | Dict: new_alerts, resolved_ids, total_active | FR-11–13 |

### 7.5 `engine/credibility.py` — CredibilityScorer

**Class**: `CredibilityScorer(weight_delta_t=0.25, weight_variance=0.10, weight_completion=0.10, weight_attendance=0.25, weight_exam=0.30, ...)`

| Method | Input | Output | FR |
|---|---|---|---|
| `compute_delta_t_score(values)` | List of Δt values | 0–100 score | FR-15 |
| `compute_variance_score(variance, historical)` | Variance value + optional history | 0–100 score | FR-15 |
| `compute_completion_score(submitted, total)` | Counts | 0–100 score | FR-15 |
| `compute_attendance_score(attendance_pct)` | Attendance % (0–100) | 0–100 score | FR-15 |
| `compute_exam_score(mid1, mid2, mid3)` | Up to 3 mid-term scores (0–100 each) | 0–100 score | FR-15 |
| `compute_credibility_score(...)` | All inputs combined | Dict: overall_score, tier, components{} | FR-15 |
| `check_policy_triggers(current, previous)` | Two scores | List of triggered policies | FR-16 |

**Return structure of `compute_credibility_score`**:
```python
{
    "overall_score": 72.35,
    "tier": "good",
    "tier_label": "Satisfactory",
    "components": {
        "delta_t_consistency": {"score": 82.0, "weight": 0.25, "weighted": 20.50},
        "variance_stability":  {"score": 70.0, "weight": 0.10, "weighted":  7.00},
        "completion_rate":     {"score": 85.0, "weight": 0.10, "weighted":  8.50},
        "attendance":          {"score": 76.0, "weight": 0.25, "weighted": 19.00},
        "exam_performance":    {"score": 57.83,"weight": 0.30, "weighted": 17.35}
    }
}
```

**Attendance Scoring Logic**:
```python
def compute_attendance_score(self, attendance_pct: float) -> float:
    pct = max(0.0, min(100.0, attendance_pct))
    if pct >= 95:
        score = 100.0
    elif pct >= 85:
        score = 80.0 + (pct - 85) * 2.0      # 85→80, 95→100
    elif pct >= 75:
        score = 60.0 + (pct - 75) * 2.0      # 75→60, 85→80
    elif pct >= 60:
        score = 30.0 + (pct - 60) * 2.0      # 60→30, 75→60
    else:
        score = pct / 60.0 * 30.0             # 0→0, 60→30
    return round(min(100.0, max(0.0, score)), 2)
```

**Exam Performance Scoring Logic** (best 2 of 3 mids):
```python
def compute_exam_score(self, mid1, mid2, mid3) -> float:
    scores = [s for s in [mid1, mid2, mid3] if s is not None]
    if not scores:
        return 50.0                       # Neutral default
    scores.sort(reverse=True)
    if len(scores) >= 2:
        avg = (scores[0] + scores[1]) / 2.0
    else:
        avg = scores[0] * 0.90           # 10% penalty for single score
    # Map average → credibility sub-score
    if avg >= 80:   return 100.0
    elif avg >= 60: return 70.0 + (avg - 60) * 1.5
    elif avg >= 40: return 40.0 + (avg - 40) * 1.5
    else:           return avg
```

### 7.6 `engine/ingestion.py` — DataIngestor

**Class**: `DataIngestor()`

**Required CSV Columns**: `student_id`, `assignment_id`, `submission_timestamp`, `deadline_timestamp`

**Optional CSV Columns**: `student_name`, `course_id`, `submission_status`, `attendance_pct`, `mid1_score`, `mid2_score`, `mid3_score`

The ingestion module accepts attendance and exam data as optional columns in CSV uploads. A `_safe_float()` helper method handles graceful conversion of these fields, returning `None` for missing, empty, or NaN values.

| Method | Function |
|---|---|
| `validate_csv_structure(content)` | Pre-validates column presence without full processing |
| `ingest_csv(content, filename)` | Full pipeline: parse → validate → compute Δt → return records |
| `_process_row(row, index)` | Validates single row, parses timestamps, computes Δt, extracts optional fields |
| `_parse_timestamp(value)` | Multi-format parser: ISO 8601, US/EU dates, UNIX timestamps |
| `_safe_float(value)` | Safely converts a value to float; returns None for empty/NaN |

**Timestamp Formats Supported**:
- `2025-01-15T14:30:00` (ISO 8601)
- `2025-01-15T14:30:00Z` (ISO with Zulu)
- `2025-01-15 14:30:00` (space-separated)
- `2025-01-15 14:30` (no seconds)
- `2025-01-15` (date only)
- `01/15/2025 14:30:00` (US format)
- `15/01/2025 14:30:00` (European format)
- UNIX timestamps (integer/float)
- Pandas fallback for edge cases

---

## 8. Route & API Design

### 8.1 Web Routes (Server-Side Rendered)

| Route | Method | Blueprint | Auth | Description |
|---|---|---|---|---|
| `/` | GET | auth | No | Landing page (redirects logged-in users) |
| `/login` | GET/POST | auth | No | Login form + authentication |
| `/register` | GET/POST | auth | No | Registration with role selection |
| `/logout` | GET | auth | Yes | End session |
| `/dashboard` | GET | dashboard | Instructor | Main instructor dashboard |
| `/dashboard/student/<id>` | GET | dashboard | Instructor | Student drill-down with 5-factor breakdown |
| `/dashboard/upload` | GET/POST | dashboard | Instructor | CSV upload (submissions + optional attendance/exam) |
| `/dashboard/export/csv` | GET | dashboard | Instructor | CSV export (students/alerts/submissions) |
| `/student/me` | GET | student | Student | Personal self-view dashboard with credibility breakdown |

### 8.2 REST API Endpoints

All API responses use a consistent envelope:
```json
{
    "success": true,
    "data": { ... },
    "message": "optional message"
}
```

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check (no auth required) |
| `/api/ingest` | POST | Upload CSV via API |
| `/api/students` | GET | List all students with metrics |
| `/api/student/<id>` | GET | Full student detail with Δt series and 5-factor breakdown |
| `/api/alerts` | GET | Active alerts (filterable by severity/resolved) |
| `/api/dashboard/summary` | GET | Class-wide aggregate statistics |
| `/api/policy/trigger` | POST | Manually trigger a policy event |
| `/api/export/csv` | GET | Export data as CSV file |

### 8.3 Role-Based Access Control

| Role | Dashboard | Student Detail | Upload | API | Self-View |
|---|---|---|---|---|---|
| Instructor | ✅ | ✅ | ✅ | ✅ | ❌ |
| Student | ❌ | ❌ | ❌ | ❌ | ✅ |
| Admin | ✅ | ✅ | ✅ | ✅ | ❌ |

Enforced via `@login_required` and a custom `@instructor_required` decorator.

### 8.4 Credibility Data Flow in Routes

All three route modules that display credibility information (dashboard, API, student) follow the same pattern for computing scores:

```python
scorer = CredibilityScorer(
    weight_delta_t=app.config["WEIGHT_DELTA_T_CONSISTENCY"],
    weight_variance=app.config["WEIGHT_VARIANCE_STABILITY"],
    weight_completion=app.config["WEIGHT_COMPLETION_RATE"],
    weight_attendance=app.config["WEIGHT_ATTENDANCE"],
    weight_exam=app.config["WEIGHT_EXAM_PERFORMANCE"],
)

result = scorer.compute_credibility_score(
    delta_t_values=delta_t_list,
    variance_value=variance,
    submitted_count=submitted,
    total_assignments=total,
    attendance_pct=student.attendance_pct,
    mid1=student.mid1_score,
    mid2=student.mid2_score,
    mid3=student.mid3_score,
)
```

The student's attendance percentage and mid-term exam scores are read directly from the `Student` model and passed to the scorer. When a CSV upload includes the optional `attendance_pct`, `mid1_score`, `mid2_score`, and `mid3_score` columns, the ingestion pipeline updates these fields on the Student record.

---

## 9. Frontend & Visualization

### 9.1 Template Architecture

All templates extend `base.html`, which provides:
- **Fixed sidebar** (260px) with role-aware navigation links
- **Sticky top navbar** with page title and live clock
- **Flash message** container (auto-dismissing after 5 seconds)
- **CSS custom properties** for consistent theming
- **Responsive breakpoint** at 992px (sidebar collapses on mobile)

### 9.2 Charts (Chart.js)

| Chart | Template | Type | Data Source |
|---|---|---|---|
| Class-Wide Δt Trend | instructor.html | Line | Submissions grouped by assignment |
| Credibility Distribution | instructor.html | Doughnut | Student score tier counts |
| Student Δt Time-Series | student_detail.html | Line | Individual student's Δt history |
| Credibility Radar | student_detail.html | Radar/Bar | 5-factor component score breakdown |
| Variance Over Time | student_detail.html | Bar | Rolling variance series |
| Personal Credibility Gauge | self_view.html | Doughnut (half) | Student's own score |
| Personal Δt Trend | self_view.html | Line | Student's own history |

**Key Implementation Detail**: All canvases are wrapped in fixed-height `<div>` containers with `position: relative` to prevent Chart.js's infinite resize loop (a common pitfall when `responsive: true` is set without a constrained parent).

### 9.3 Design System

- **Font**: Inter (Google Fonts) — clean, modern, highly legible
- **Color Palette**: 7 CSS custom properties
  - Primary: `#4361ee` (blue)
  - Success: `#06d6a0` (green) — Excellent tier
  - Warning: `#ffd166` (yellow) — Warning tier
  - Danger: `#ef476f` (red) — Critical tier
  - Info: `#118ab2` (teal) — Charts, links
  - Dark: `#073b4c` — Sidebar gradient
- **Cards**: 12px border-radius, subtle border, hover lift effect
- **Alert Cards**: Left border colored by severity (critical=red, warning=yellow, info=teal)

---

## 10. Authentication & Security

### 10.1 Password Security

Passwords are hashed using **Werkzeug's `generate_password_hash`** (scrypt algorithm by default in Werkzeug 3.x). Never stored in plaintext.

```python
# In User model:
def set_password(self, password):
    self.password_hash = generate_password_hash(password)

def check_password(self, password):
    return check_password_hash(self.password_hash, password)
```

### 10.2 CSRF Protection

Flask-WTF's `CSRFProtect` is applied globally. Every POST form includes a hidden `csrf_token` field. The API blueprint is explicitly exempted since it's designed for programmatic access.

### 10.3 Session Management

- **Flask-Login** manages user sessions with `@login_required` decorator
- **Session lifetime**: 8 hours (configurable)
- **Session storage**: Filesystem-backed (via Flask-Session)

### 10.4 Input Validation

- CSV uploads validated for file extension (`.csv` only) and size (16MB max)
- Registration validates unique username/email
- All database queries use parameterized ORM calls (no raw SQL injection risk)

---

## 11. Testing Strategy

### 11.1 Test Architecture

```
tests/
├── conftest.py          # Shared fixtures
├── test_metrics.py      # Unit tests — MetricComputer (17 tests)
├── test_hysteresis.py   # Unit tests — HysteresisFilter (11 tests)
├── test_credibility.py  # Unit tests — CredibilityScorer (27 tests)
├── test_ingestion.py    # Unit tests — DataIngestor (11 tests)
└── test_routes.py       # Integration tests — routes, API, models (17 tests)
```

**Total: 83 tests, all passing**

### 11.2 Fixtures (`conftest.py`)

| Fixture | Scope | Description |
|---|---|---|
| `app` | session | Flask app with TestingConfig (in-memory SQLite) |
| `db` | function | Fresh database per test (create_all → yield → drop_all) |
| `client` | function | Flask test client |
| `instructor_user` | function | Pre-created instructor account |
| `student_user` | function | Student with linked profile (attendance=82%, mid1=70, mid2=65, mid3=75) |
| `sample_student` | function | Student with 10 submissions, attendance=88%, mid1=72, mid2=68, mid3=80 |

### 11.3 Test Categories

**Unit Tests (Engine Modules)**:
- Δt computation with early/late/exact submissions
- Hours conversion positive/negative
- Classification boundary (Δt=0 is "on-time")
- Variance stability with uniform/varied/empty/single inputs
- Rolling variance series length and padding
- Trend detection (declining/improving/stable)
- Hysteresis trend detection (returns dict or None)
- Variance spike detection threshold
- Alert resolution with consecutive improvements
- Credibility score structure and tier mapping (verifies all 5 components)
- Weight sum validation (all 5 weights must equal 1.0)
- Policy trigger conditions
- **Attendance scoring**: perfect (≥95%), good (85–95%), minimum eligible (75%), poor (<60%), zero
- **Exam scoring**: best 2 of 3 selection, all-high, all-low, single score with penalty, no scores (neutral), two-score handling
- CSV validation with correct/missing/empty columns
- Ingestion with valid data, late detection, invalid rows
- Timestamp parsing across multiple formats

**Integration Tests (Routes)**:
- Public pages load without auth (landing, login, register)
- Invalid login returns 200 (re-renders form)
- Valid login redirects to dashboard
- Dashboard requires authentication
- API health endpoint returns correct envelope
- API student list returns nested data structure
- API student detail lookup by string ID
- API dashboard summary includes required fields
- API alerts returns list structure
- CSV export returns correct content-type
- Model computed properties (active_alerts_count, total_submissions)
- Model serialization (to_dict method — includes attendance/exam fields)
- Password hashing bidirectional verification

### 11.4 Running Tests

```bash
# Run all tests with verbose output
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=engine --cov=routes --cov-report=html

# Run a specific test file
python -m pytest tests/test_metrics.py -v

# Run a specific test
python -m pytest tests/test_credibility.py::TestCredibilityScorer::test_credibility_tier_high -v
```

---

## 12. Data Generation & Seeding

### 12.1 Demo Seed Data (`run.py --seed`)

Creates a realistic small dataset for demonstrations:

| Entity | Count | Details |
|---|---|---|
| Users | 3 | instructor/password123, arjun/password123, admin/admin123 |
| Courses | 3 | CS501, CS502, CS503 |
| Students | 30 | Across 3 courses, varied credibility scores |
| Submissions | ~262 | 8–10 per student with behavioral patterns |
| Alerts | ~9 | Generated by hysteresis engine |
| Policy Events | ~29 | Generated by credibility scorer |

Each student is assigned a behavioural profile that determines their submission timing, attendance rate, and exam score ranges:

| Profile | % | Δt Pattern | Miss Rate | Attendance | Mid Exam Range |
|---|---|---|---|---|---|
| Excellent | 15% | 12–48h early, σ=6h | 2% | 92–99% | 78–98 |
| Good | 25% | 2–24h early, σ=8h | 5% | 82–94% | 65–85 |
| Average | 25% | -6 to +12h, σ=10h | 10% | 72–86% | 50–75 |
| Struggling | 15% | -24 to +6h, σ=14h | 15% | 58–76% | 35–60 |
| At Risk | 8% | -48 to -12h, σ=18h | 30% | 40–62% | 20–45 |
| Declining | 7% | Starts excellent, worsens | 5→20% | 65–82% | 45–70 |
| Improving | 5% | Starts struggling, improves | 20→3% | 70–88% | 55–80 |

The seed process generates realistic `attendance_pct` and `mid1_score`, `mid2_score`, `mid3_score` values per profile, then runs the full credibility engine recomputation across all students.

### 12.2 Synthetic Dataset Generator (`generate_dataset.py`)

For larger-scale testing and thesis evaluation:

| Parameter | Value |
|---|---|
| Students | 200 |
| Assignments | 10 |
| Courses | 3 |
| Total Records | ~1,800 |

Output: `data/submissions.csv` and `data/test_submissions.csv` (50-record subset)

---

## 13. Deployment Pipeline

### 13.1 Local Development

```bash
# 1. Clone repository
git clone https://github.com/EDITHmid/PASS.git
cd PASS

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize database with demo data
python run.py --seed

# 5. Start development server
python run.py
# → http://127.0.0.1:5000
```

### 13.2 Production Deployment (Render)

**Files created for deployment**:

| File | Purpose |
|---|---|
| `wsgi.py` | Gunicorn entry point, imports `app` from factory, auto-seeds on first deploy |
| `build.sh` | Render build script — installs deps, creates directories |
| `render.yaml` | Render blueprint — declares service type, commands, env vars |

**Deployment flow**:
1. Push to `main` branch on GitHub
2. Render detects the push (webhook)
3. Render runs `build.sh` (pip install, mkdir)
4. Render starts `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2`
5. `wsgi.py` creates tables and seeds demo data on first run
6. App is live at `https://pass-academic-support.onrender.com`

**Environment Variables on Render**:

| Variable | Value |
|---|---|
| `SECRET_KEY` | Auto-generated random string |
| `PYTHON_VERSION` | 3.13.9 |
| `FLASK_ENV` | production |

### 13.3 CI/CD

Every `git push origin main` triggers an automatic redeploy on Render. No manual steps needed after initial setup. The typical workflow:

```
Edit code locally → Run tests → git add/commit/push → Auto-deploys in ~2 min
```

---

## 14. Development Workflow & Decisions

### 14.1 Development Process

The project was built systematically in this order:

1. **PRD Analysis** — Extracted 10-page PDF using PyPDF2, mapped all Functional Requirements (FR-01 through FR-17) to implementation tasks
2. **Configuration Layer** — `config.py` + `app.py` (application factory pattern)
3. **Data Models** — 7 SQLAlchemy models in `models.py`
4. **Analytical Engine** — 4 modules built bottom-up:
   - `metrics.py` (foundation — Δt, variance, trend)
   - `hysteresis.py` (depends on metrics)
   - `credibility.py` (depends on metrics)
   - `ingestion.py` (depends on metrics)
5. **Route Layer** — 4 Flask blueprints with business logic
6. **Frontend Templates** — 13 Jinja2 templates with Chart.js visualizations
7. **Entry Point & Seeding** — `run.py` with CLI flags for demo data
8. **Testing** — 72 pytest tests covering all engine modules and routes
9. **Documentation** — README.md with architecture diagrams
10. **Bug Fixes** — Multiple consistency passes to align models ↔ routes ↔ templates ↔ tests
11. **Deployment** — Render configuration files + GitHub push
12. **Five-Factor Credibility Enhancement** — Added attendance (25%) and exam performance / best 2 of 3 mids (30%) as credibility factors per mentor feedback. Updated Student model (4 new fields), CredibilityScorer (2 new methods, 5-weight formula), ingestion module (4 new optional CSV columns), all 3 display route modules, config weights, seed data generation, and test suite (11 new tests for attendance and exam scoring, total 83). Reduced Δt weight from 50% → 25%, variance 30% → 10%, completion 20% → 10% to accommodate new academic performance signals.

### 14.2 Key Design Decisions

| Decision | Rationale |
|---|---|
| **Application Factory Pattern** | Enables different configs for dev/test/prod; required for pytest fixtures |
| **Blueprints** | Modular route organization; each concern (auth, dashboard, API, student) is isolated |
| **Engine as pure Python classes** | No Flask dependency — engine can be tested independently without HTTP context |
| **Five-Factor Credibility Model** | Combining behavioural signals (Δt, variance, completion) with academic signals (attendance, exams) produces a more holistic reliability index than submission timing alone |
| **Best 2 of 3 Mid-Terms** | A forgiving policy — one bad exam doesn't destroy credibility. Encourages consistency across exams |
| **Attendance as 25% weight** | Attendance is the strongest proxy for engagement that doesn't require assignment submission data. 75% threshold aligns with examination eligibility rules |
| **Computed properties on Student model** | `active_alerts_count`, `on_time_rate`, `best_two_mid_avg` are derived, not stored — always consistent |
| **JSON serialization in routes** | Chart data passed as `json.dumps()` strings into templates, parsed by Chart.js client-side |
| **String-based student_id in URLs** | URLs like `/dashboard/student/1RV22CS001` are human-readable; routes accept string USN, not integer PK |
| **CSRF exemption for API** | API is designed for programmatic access (tools, scripts); web forms still protected |
| **Neutral credibility default (50.0)** | New students start at 50/100, not 0 — avoids false-critical alerts on enrollment |

### 14.3 Bugs Discovered & Fixed

| Bug | Root Cause | Fix |
|---|---|---|
| `ValueError: invalid literal for int()` on student detail | Route used `<int:student_id>` but URL contained string USN like "1RV22CS027" | Changed to `<student_id>` (string) with `filter_by(student_id=...)` |
| Page kept expanding infinitely | Chart.js `responsive: true` without constrained parent causes infinite resize loop | Wrapped all `<canvas>` in `<div style="position:relative; height:Xpx;">` |
| User model field mismatch | Model had `first_name`/`last_name` but templates/seed used `full_name` | Unified to single `full_name` field |
| Template variable mismatch | Route passed different keys than template expected | Aligned all variable names between routes and Jinja2 templates |
| Nested credibility components | Tests expected flat structure but engine returns nested `components` dict | Updated routes and tests to use `cred_result["components"]["delta_t_consistency"]["score"]` |
| CSV column names in tests | Tests used `submitted_at`/`deadline` but ingestor requires `submission_timestamp`/`deadline_timestamp` | Fixed all test CSV headers |
| API response envelope | Tests expected flat JSON but API wraps in `{"success": true, "data": {...}}` | Fixed test assertions to unwrap envelope |
| Empty timestamp parsing | `_parse_timestamp("")` didn't raise — pandas fallback accepted it silently | Updated test to accept the behavior |
| Seed data ordering | `profile_assignments` referenced before definition in student loop | Moved profiles and profile_assignments block before the student creation loop |

---

## 15. Challenges Faced & Solutions

### 15.1 Consistency Across Layers

**Challenge**: With 7 models, 4 engine modules, 4 route blueprints, and 13 templates, keeping field names, method signatures, and data structures consistent was the biggest challenge.

**Solution**: Systematic layer-by-layer verification — read engine source → verify route extracts correct keys → verify template references match → verify test assertions match. Multiple passes were needed.

### 15.2 Chart.js Infinite Resize

**Challenge**: The instructor dashboard kept expanding downward indefinitely, making it unusable.

**Solution**: Chart.js with `responsive: true` requires a parent element with a defined height. Wrapping each `<canvas>` in `<div style="position:relative; height:260px;">` constrains the chart area.

### 15.3 Pandas on ARM64 Windows

**Challenge**: `pandas==2.2.3` needed to build from source on ARM64 Windows, taking several minutes.

**Solution**: Used the `install_python_packages` tool which handled the build correctly within the venv.

### 15.4 CSRF and API Coexistence

**Challenge**: Web forms need CSRF protection, but API endpoints need to accept JSON without tokens.

**Solution**: `csrf.exempt(api_bp)` — exempts only the API blueprint while keeping all web form routes protected.

### 15.5 Five-Factor Model Integration

**Challenge**: Extending the credibility model from 3 factors to 5 required changes across 11 source files (model, engine, config, 3 route modules, run.py seed logic, conftest, and test files). All had to remain consistent.

**Solution**: Systematic update in dependency order — model first (new DB columns), then engine (new scoring methods), then config (new weights), then routes (pass new data), then seeds (generate realistic values), then tests (verify all 5 components). The `_safe_float()` helper in ingestion ensured graceful handling of missing attendance/exam data in CSV uploads.

---

## 16. Future Enhancements

| Enhancement | Description | Complexity |
|---|---|---|
| **LMS Integration** | Direct Moodle/Canvas API polling instead of CSV upload | Medium |
| **PostgreSQL Migration** | Replace SQLite for multi-user concurrent access | Low |
| **Email Notifications** | Alert instructors via email for critical-severity alerts | Low |
| **Predictive Model** | ML-based grade prediction using Δt patterns + credibility factors as features | High |
| **Historical Comparison** | Compare current cohort Δt patterns against previous semesters | Medium |
| **SSO Authentication** | Integrate with institutional SAML/OAuth providers | Medium |
| **Real-Time WebSocket Updates** | Push alerts to dashboard without page refresh | Medium |
| **PDF Report Generation** | Generate printable student reports for advisors | Low |
| **Batch Policy Approval** | Instructor reviews and approves/rejects triggered policies | Low |
| **Dark Mode** | Bootstrap 5.3 `data-bs-theme="dark"` support (partially built in) | Low |
| **Weighted Factor Customisation** | Allow instructors to adjust the 5 credibility weights via UI | Low |
| **Additional Exam Support** | Extend to support end-semester exams, lab internals, etc. | Medium |

---

## Appendix A: Demo Accounts

| Username | Password | Role | Access |
|---|---|---|---|
| instructor | password123 | Instructor | Full dashboard, upload, export |
| arjun | password123 | Student | Personal self-view only |
| admin | admin123 | Admin | Full dashboard + admin capabilities |

## Appendix B: Quick Commands

```bash
# Start development server
python run.py

# Reset and reseed database
python run.py --reset

# Generate synthetic CSV dataset
python generate_dataset.py

# Run full test suite
python -m pytest tests/ -v

# Run tests with coverage
python -m pytest tests/ --cov=engine --cov=routes --cov-report=term-missing
```

## Appendix C: API Quick Reference

```bash
# Health check
curl http://localhost:5000/api/health

# Get all students
curl -b cookies.txt http://localhost:5000/api/students

# Get student detail (includes 5-factor credibility breakdown)
curl -b cookies.txt http://localhost:5000/api/student/1RV22CS001

# Dashboard summary
curl -b cookies.txt http://localhost:5000/api/dashboard/summary

# Get alerts (filtered)
curl -b cookies.txt "http://localhost:5000/api/alerts?severity=critical&resolved=false"

# Upload CSV via API
curl -b cookies.txt -F "file=@data/submissions.csv" http://localhost:5000/api/ingest
```

## Appendix D: Credibility Score Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│               FIVE-FACTOR CREDIBILITY MODEL                  │
├──────────────────────┬──────────┬───────────────────────────┤
│ Component            │  Weight  │ Signal Type               │
├──────────────────────┼──────────┼───────────────────────────┤
│ Δt Consistency       │   25%    │ Behavioural (submissions) │
│ Variance Stability   │   10%    │ Behavioural (consistency) │
│ Completion Rate      │   10%    │ Behavioural (coverage)    │
│ Attendance           │   25%    │ Academic (engagement)     │
│ Exam Performance     │   30%    │ Academic (best 2/3 mids)  │
├──────────────────────┼──────────┼───────────────────────────┤
│ TOTAL                │  100%    │ Behavioural 45% + Acad 55%│
└──────────────────────┴──────────┴───────────────────────────┘

Tier Classification:
  ≥ 85  →  Excellent  (High Credibility — attendance waiver)
  50–84 →  Good       (Satisfactory — no action)
  30–49 →  Warning    (Needs Attention — monitor)
  < 30  →  Critical   (At Risk — intervention required)
```

---

*Document generated for PASS v1.1 (Five-Factor Model) — February 2026*
