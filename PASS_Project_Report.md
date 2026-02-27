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

PASS addresses both problems by:

1. **Computing Submission Velocity (Δt)** — a signed temporal distance metric that captures not just *whether* a student is late, but *how their pattern is changing over time*.
2. **Applying Hysteresis Filtering** — requiring a negative trend to persist for 2–3 consecutive assignments before generating an alert, suppressing transient noise.
3. **Building a Credibility Score** — a dynamic 0–100 reliability index combining Δt consistency (50%), variance stability (30%), and completion rate (20%).
4. **Automating Low-Stakes Policies** — high-credibility students automatically receive perks (attendance waivers); declining students trigger proactive interventions.

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
│  │  trend)   │ │ (alerts)     │ │ (0–100)      │              │
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
│  (ingestion.py)  │   normalizes to UTC, computes initial Δt
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
│ CredibilityScorer│ ← Computes weighted composite score (50/30/20),
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
│   ├── credibility.py              # Credibility scoring, policy triggers
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
└──────────┘                                               └─────┬──────┘
     │                                                           │
     │ 1:1                                          1:N │  1:N │  1:N │
     └──────────────▶ Student                           │      │      │
                                                        ▼      ▼      ▼
                                                ┌──────────┐ ┌─────┐ ┌───────────┐
                                                │Submission│ │Alert│ │PolicyEvent│
                                                │──────────│ │─────│ │───────────│
                                                │ id (PK)  │ │ id  │ │ id (PK)   │
                                                │ sub_id   │ │ met │ │ policy    │
                                                │ stud FK  │ │ pct │ │ student FK│
                                                │ assign   │ │ sev │ │ type      │
                                                │ delta_t  │ │ desc│ │ desc      │
                                                │ deadline │ │ res │ │ triggered │
                                                │ status   │ └─────┘ │ active    │
                                                └──────────┘         └───────────┘

                    ┌───────────────┐
                    │ IngestionLog  │ (standalone — tracks CSV upload history)
                    │───────────────│
                    │ id, filename  │
                    │ records, errs │
                    │ ingested_by FK│
                    └───────────────┘
```

### 5.2 Model Specifications

#### User
| Column | Type | Description |
|---|---|---|
| id | Integer PK | Auto-increment primary key |
| username | String(80) | Unique login identifier |
| email | String(120) | Unique email address |
| password_hash | String(256) | Werkzeug scrypt hash |
| full_name | String(100) | Display name |
| role | String(20) | "instructor", "student", or "admin" |
| is_active | Boolean | Account status (default True) |
| created_at | DateTime | Account creation timestamp (UTC) |
| last_login | DateTime | Last login timestamp |

#### Student
| Column | Type | Description |
|---|---|---|
| id | Integer PK | Internal primary key |
| student_id | String(20) | University Serial Number e.g., "1RV22CS001" |
| name | String(100) | Student full name |
| course_id | Integer FK | Links to Course |
| user_id | Integer FK | Links to User (optional 1:1) |
| credibility_score | Float | Dynamic 0–100 score (default 50.0) |
| attendance_pct | Float | Attendance percentage 0–100 (default 0.0) |
| mid1_score | Float | Mid-term 1 exam score (0–100, nullable) |
| mid2_score | Float | Mid-term 2 exam score (0–100, nullable) |
| mid3_score | Float | Mid-term 3 exam score (0–100, nullable) |
| enrollment_date | DateTime | Date of enrollment |
| status | String(20) | "active" or "inactive" |

**Computed Properties** (not stored, calculated on access):
- `active_alerts_count` — count of unresolved alerts
- `total_submissions` — total submission records
- `on_time_rate` — percentage of on-time submissions

#### Submission
| Column | Type | Description |
|---|---|---|
| id | Integer PK | Internal primary key |
| submission_id | String(20) | Unique external ID (e.g., "SUB-A3F8C2D1E9") |
| student_id | Integer FK | Links to Student.id |
| assignment_id | String(20) | Assignment identifier (e.g., "A01") |
| course_id_ref | Integer FK | Links to Course |
| submitted_at | DateTime | Actual submission timestamp |
| deadline | DateTime | Assignment deadline timestamp |
| delta_t | Float | Δt in seconds (positive = early, negative = late) |
| delta_t_hours | Float | Δt converted to hours |
| submission_status | String(20) | "on-time", "late", or "missing" |

#### Alert
| Column | Type | Description |
|---|---|---|
| id | Integer PK | Internal primary key |
| alert_id | String(20) | Unique external alert ID |
| student_id | Integer FK | Links to Student.id |
| metric | String(20) | "delta_t" or "variance" |
| pct_change | Float | Percentage change that triggered alert |
| window_size | Integer | Number of assignments in detection window |
| severity | String(20) | "info", "warning", or "critical" |
| description | Text | Human-readable alert description |
| resolved | Boolean | Whether alert has been resolved |
| resolved_at | DateTime | Timestamp of resolution |
| consecutive_improvements | Integer | Count of consecutive improving submissions |
| created_at | DateTime | Alert creation timestamp |

#### PolicyEvent
| Column | Type | Description |
|---|---|---|
| id | Integer PK | Internal primary key |
| event_id | String(20) | Unique external event ID |
| student_id | Integer FK | Links to Student.id |
| policy_type | String(50) | "attendance_waiver", "recognition", "intervention_required" |
| description | Text | Policy event details |
| triggered_at | DateTime | When the policy was triggered |
| expires_at | DateTime | Expiration date (if applicable) |
| is_active | Boolean | Whether the policy is currently active |
| triggered_by | String(20) | What triggered it ("system" or "manual") |

#### IngestionLog
| Column | Type | Description |
|---|---|---|
| id | Integer PK | Internal primary key |
| filename | String(255) | Original CSV filename |
| source | String(20) | "csv" or "api" |
| total_records | Integer | Total rows in the file |
| valid_records | Integer | Successfully processed rows |
| invalid_records | Integer | Skipped rows |
| errors | Text | Error log (newline-separated) |
| status | String(20) | "completed", "failed", or "partial" |
| ingested_by | Integer FK | User who performed the upload |
| created_at | DateTime | Ingestion timestamp |

---

## 6. Core Algorithms

### 6.1 Submission Velocity — Δt (Delta-t)

**Definition**: The signed temporal distance between a submission timestamp and its assignment deadline.

```
Δt = deadline_timestamp − submission_timestamp (in seconds)
```

| Δt Value | Meaning |
|---|---|
| Δt > 0 | Submitted *before* the deadline (early) |
| Δt = 0 | Submitted exactly at the deadline |
| Δt < 0 | Submitted *after* the deadline (late) |

**Why seconds?** Using raw seconds avoids precision loss during intermediate calculations. The value is converted to hours (`delta_t_hours = delta_t / 3600`) only for display purposes.

**Implementation** (`engine/metrics.py`):
```python
def compute_delta_t(self, submission_timestamp, deadline_timestamp):
    return deadline_timestamp - submission_timestamp
```

### 6.2 Variance Stability — Rolling σ

**Definition**: The population standard deviation of the most recent N Δt values (default N=5), measuring submission pattern consistency.

```
σ = sqrt( (1/N) * Σ(Δt_i − μ)² )   for i in last N submissions
```

- **Low σ** → Student submits at consistent intervals (good)
- **High σ** → Erratic submission pattern (concerning)

**Why population σ, not sample σ?** We're measuring the variance of the *actual* window, not estimating a population parameter. Population std dev (dividing by N) is appropriate here.

**Rolling Series**: For each submission index i, compute σ over the window `[i-N+1, i]`. The first element is always `None` (insufficient data). This produces a time-series for charting.

### 6.3 Hysteresis Filtering

**Problem**: A student submits late once → simple threshold generates alert → student submits on-time next → alert resolved → student submits late again → new alert. This oscillation causes alert fatigue.

**Solution**: Hysteresis requires a trend to **persist for W consecutive assignments** (default W=3) before generating an alert. This is adapted from signal processing electrical engineering, specifically the Schmitt trigger.

```
  Alert Generation:
  ─────────────────
  IF the last W Δt values show a consistent decline:
    pct_change = ((latest - earliest) / |earliest|) * 100
    IF pct_change ≤ threshold:
      Generate alert with severity based on magnitude
      
  Alert Resolution:
  ─────────────────
  IF R consecutive improving submissions (default R=2):
    Resolve the alert
    Reset improvement counter
```

**Severity Classification**:
| Threshold | Severity |
|---|---|
| pct_change ≥ 50% | Critical |
| pct_change ≥ 25% | Warning |
| pct_change < 25% | Info |

**Variance Spike Detection**: Independently monitors variance values. If the recent window's average variance exceeds `threshold_multiplier × historical_mean` (default 2.0×), a variance-type alert is generated.

### 6.4 Credibility Score

**Definition**: A dynamic 0–100 composite reliability index per student, computed from five weighted factors.

```
Credibility = 0.25 × Δt_Consistency + 0.10 × Variance_Stability + 0.10 × Completion_Rate
           + 0.25 × Attendance + 0.30 × Exam_Performance
```

**Component Calculations**:

**Δt Consistency Score (0–100) — 25%**:
```
For each Δt value, compute individual score:
  score_i = clamp(0, 100, 60 + (Δt_hours_i / 24) × 40)
  
  Anchors:
    Δt ≥ +24h → 100 (submitted a full day early)
    Δt =   0h →  60 (exactly on time)  
    Δt ≤ -24h →   0 (a full day late)
    
Final = average(all score_i)
```

**Variance Stability Score (0–100) — 10%**:
```
Convert variance to hours: var_hours = variance / 3600
Diminishing penalty curve:
  score = 100 × exp(-var_hours / 12)
  
If historical variances provided, also factor in relative comparison.
```

**Completion Rate Score (0–100) — 10%**:
```
ratio = submitted_count / total_assignments
Non-linear penalty (harsher for low completion):
  score = 100 × ratio^1.5
```

**Attendance Score (0–100) — 25%**:
```
Non-linear mapping based on institutional attendance norms:
  ≥ 95%  →  100  (exemplary)
  ≥ 85%  →   80–100
  ≥ 75%  →   60–80  (minimum exam eligibility threshold)
  ≥ 60%  →   30–60
  < 60%  →   0–30  (linear to zero)

Rationale: 75% is the standard minimum attendance threshold
for examination eligibility in Indian universities.
```

**Exam Performance Score (0–100) — 30%**:
```
Best 2 of 3 mid-term exams (Mid-1, Mid-2, Mid-3) are selected
and averaged:
  sorted_scores = sort(mid1, mid2, mid3, descending)
  avg = (sorted_scores[0] + sorted_scores[1]) / 2

Mapping to credibility sub-score:
  avg ≥ 80  →  100
  avg ≥ 60  →   70–100 (linear)
  avg ≥ 40  →   40–70  (linear)
  avg < 40  →    0–40  (linear)

If only 1 mid score available: avg = score × 0.90 (10% penalty)
If no scores available: neutral default = 50
```

**Tier Classification**:
| Score Range | Tier | Label |
|---|---|---|
| ≥ 85 | Excellent | Highly reliable |
| 50–84 | Good | Generally consistent |
| 30–49 | Warning | Needs attention |
| < 30 | Critical | Immediate intervention needed |

### 6.5 Automated Policy Triggers

When a credibility score is computed, the system checks for policy-triggering conditions:

| Condition | Policy |
|---|---|
| Score crosses ≥ 85 (upward) | `attendance_waiver` — automated perk for reliable students |
| Score improvement > 15 points | `recognition` — positive reinforcement |
| Score drops below 30 | `intervention_required` — flag for instructor follow-up |

---

## 7. Module-by-Module Implementation

### 7.1 `app.py` — Application Factory

Uses the **Application Factory Pattern** (Flask best practice):

```python
def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    CORS(app)
    
    # Register 4 blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(student_bp, url_prefix="/student")
    
    # CSRF exempt for API (stateless JSON endpoints)
    csrf.exempt(api_bp)
    
    # Error handlers (404, 500, 403)
    # Context processor (injects app_name, version, full_name)
    # Create tables on startup
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
- `HYSTERESIS_WINDOW_SIZE = 3`
- `HYSTERESIS_REVERSAL_COUNT = 2`
- `VARIANCE_ROLLING_WINDOW = 5`
- `CREDIBILITY_THRESHOLD_HIGH = 85`
- `WEIGHT_DELTA_T_CONSISTENCY = 0.50`
- etc.

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

**Class**: `CredibilityScorer(weight_delta_t=0.50, weight_variance=0.30, weight_completion=0.20, ...)`

| Method | Input | Output | FR |
|---|---|---|---|
| `compute_delta_t_score(values)` | List of Δt values | 0–100 score | FR-15 |
| `compute_variance_score(variance, historical)` | Variance value + optional history | 0–100 score | FR-15 |
| `compute_completion_score(submitted, total)` | Counts | 0–100 score | FR-15 |
| `compute_credibility_score(...)` | All inputs combined | Dict: overall_score, tier, components{} | FR-15 |
| `check_policy_triggers(current, previous)` | Two scores | List of triggered policies | FR-16 |

**Return structure of `compute_credibility_score`**:
```python
{
    "overall_score": 78.5,
    "tier": "good",
    "tier_label": "Generally consistent",
    "components": {
        "delta_t_consistency": {"score": 82.0, "weight": 0.50, "weighted": 41.0},
        "variance_stability": {"score": 70.0, "weight": 0.30, "weighted": 21.0},
        "completion_rate":    {"score": 82.5, "weight": 0.20, "weighted": 16.5}
    }
}
```

### 7.6 `engine/ingestion.py` — DataIngestor

**Class**: `DataIngestor()`

**Required CSV Columns**: `student_id`, `assignment_id`, `submission_timestamp`, `deadline_timestamp`

**Optional CSV Columns**: `student_name`, `course_id`, `submission_status`

| Method | Function |
|---|---|
| `validate_csv_structure(content)` | Pre-validates column presence without full processing |
| `ingest_csv(content, filename)` | Full pipeline: parse → validate → compute Δt → return records |
| `_process_row(row, index)` | Validates single row, parses timestamps, computes Δt |
| `_parse_timestamp(value)` | Multi-format parser: ISO 8601, US/EU dates, UNIX timestamps |

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
| `/dashboard/student/<id>` | GET | dashboard | Instructor | Student drill-down |
| `/dashboard/upload` | GET/POST | dashboard | Instructor | CSV upload |
| `/dashboard/export/csv` | GET | dashboard | Instructor | CSV export (students/alerts/submissions) |
| `/student/me` | GET | student | Student | Personal self-view dashboard |

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
| `/api/student/<id>` | GET | Full student detail with Δt series |
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
| Credibility Radar | student_detail.html | Radar/Bar | Component score breakdown |
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
| `student_user` | function | Student with linked Student profile |
| `sample_student` | function | Student with 10 submissions (varied Δt values) |

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
- Credibility score structure and tier mapping
- Weight sum validation (must equal 1.0)
- Policy trigger conditions
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
- Model serialization (to_dict method)
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
| Submissions | ~276 | 8–10 per student with behavioral patterns |
| Alerts | ~6 | Generated by hysteresis engine |
| Policy Events | ~19 | Generated by credibility scorer |

### 12.2 Synthetic Dataset Generator (`generate_dataset.py`)

For larger-scale testing and thesis evaluation:

| Parameter | Value |
|---|---|
| Students | 200 |
| Assignments | 10 |
| Courses | 3 |
| Total Records | ~1,800 |

**7 Behavioral Profiles**:

| Profile | % | Δt Pattern | Miss Rate |
|---|---|---|---|
| Excellent | 15% | 12–48h early, σ=6h | 2% |
| Good | 25% | 2–24h early, σ=8h | 5% |
| Average | 25% | -6 to +12h, σ=10h | 10% |
| Struggling | 15% | -24 to +6h, σ=14h | 15% |
| At Risk | 8% | -48 to -12h, σ=18h | 30% |
| Declining | 7% | Starts excellent, progressively worsens | 5→20% |
| Improving | 5% | Starts struggling, progressively improves | 20→3% |

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

### 14.2 Key Design Decisions

| Decision | Rationale |
|---|---|
| **Application Factory Pattern** | Enables different configs for dev/test/prod; required for pytest fixtures |
| **Blueprints** | Modular route organization; each concern (auth, dashboard, API, student) is isolated |
| **Engine as pure Python classes** | No Flask dependency — engine can be tested independently without HTTP context |
| **Computed properties on Student model** | `active_alerts_count`, `on_time_rate` are derived, not stored — always consistent |
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

---

## 16. Future Enhancements

| Enhancement | Description | Complexity |
|---|---|---|
| **LMS Integration** | Direct Moodle/Canvas API polling instead of CSV upload | Medium |
| **PostgreSQL Migration** | Replace SQLite for multi-user concurrent access | Low |
| **Email Notifications** | Alert instructors via email for critical-severity alerts | Low |
| **Predictive Model** | ML-based grade prediction using Δt patterns as features | High |
| **Historical Comparison** | Compare current cohort Δt patterns against previous semesters | Medium |
| **SSO Authentication** | Integrate with institutional SAML/OAuth providers | Medium |
| **Real-Time WebSocket Updates** | Push alerts to dashboard without page refresh | Medium |
| **PDF Report Generation** | Generate printable student reports for advisors | Low |
| **Batch Policy Approval** | Instructor reviews and approves/rejects triggered policies | Low |
| **Dark Mode** | Bootstrap 5.3 `data-bs-theme="dark"` support (partially built in) | Low |

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

# Get student detail
curl -b cookies.txt http://localhost:5000/api/student/1RV22CS001

# Dashboard summary
curl -b cookies.txt http://localhost:5000/api/dashboard/summary

# Get alerts (filtered)
curl -b cookies.txt "http://localhost:5000/api/alerts?severity=critical&resolved=false"

# Upload CSV via API
curl -b cookies.txt -F "file=@data/submissions.csv" http://localhost:5000/api/ingest
```

---

*Document generated for PASS v1.0 — February 2026*
