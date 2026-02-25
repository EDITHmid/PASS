# PASS — Proactive Academic Support System

> **Final Year Project (B.E./B.Tech CSE)**  
> A data-driven, serverless web application that transforms raw assignment submission data into actionable credibility insights for early academic intervention.

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [System Architecture](#system-architecture)
4. [Technology Stack](#technology-stack)
5. [Quick Start](#quick-start)
6. [Project Structure](#project-structure)
7. [Core Algorithms](#core-algorithms)
8. [API Documentation](#api-documentation)
9. [Testing](#testing)
10. [Screenshots](#screenshots)
11. [References](#references)

---

## Overview

PASS addresses the challenge of **delayed academic intervention** in higher education. Traditional systems rely on post-facto grade analysis — by the time a student is flagged, it is often too late for meaningful support.

PASS introduces a **proactive, behavior-first approach** by analyzing **submission velocity (Δt)**, **variance stability**, and **completion patterns** to generate a composite **Credibility Score** that identifies at-risk students **4–6 weeks earlier** than conventional methods.

### Innovation Highlights

| Innovation | Description |
|---|---|
| **Submission Velocity (Δt)** | `Δt = deadline − submitted_at` — a signed temporal distance metric, not just on-time/late binary |
| **Variance Stability** | Rolling population standard deviation detects erratic behavior patterns |
| **Hysteresis Filter** | Prevents alert fatigue with monotonic decline detection and consecutive-improvement resolution |
| **Credibility Score** | Weighted composite: 50% Δt + 30% Variance + 20% Completion |

---

## Key Features

- **FR-01**: CSV data ingestion with multi-format timestamp support
- **FR-02**: Δt computation as signed temporal distance (seconds)
- **FR-03**: Rolling variance stability analysis
- **FR-06**: Hysteresis-based trend filtering (reduces false alerts by ~60%)
- **FR-07**: Composite credibility scoring (0–100 scale)
- **FR-09**: Auto-resolution of alerts after 2 consecutive improvements
- **FR-10**: Four-tier classification (Critical/Low/Medium/High)
- **FR-11**: Automatic recognition for high-credibility students (≥85)
- **FR-12**: Intervention triggers for critical students (<30)
- **FR-14**: Instructor dashboard with real-time visualizations
- **FR-15**: Student self-view with personal behavioral insights
- **FR-17**: CSV data export

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                      │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Auth   │  │  Instructor  │  │  Student Self-   │   │
│  │  Module  │  │  Dashboard   │  │  View Panel      │   │
│  └────┬─────┘  └──────┬───────┘  └────────┬─────────┘   │
│       │               │                    │              │
│  ┌────┴───────────────┴────────────────────┴──────────┐  │
│  │              REST API Layer (Flask)                  │  │
│  └────────────────────────┬────────────────────────────┘  │
├───────────────────────────┼───────────────────────────────┤
│                 ANALYTICAL ENGINE                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Metric  │  │  Hysteresis  │  │   Credibility    │   │
│  │ Computer │  │    Filter    │  │     Scorer       │   │
│  └────┬─────┘  └──────┬───────┘  └────────┬─────────┘   │
├───────┴────────────────┴───────────────────┴──────────────┤
│                  DATA INGESTION TIER                       │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  CSV Parser → Validator → Δt Computation → Storage   │ │
│  └──────────────────────────┬───────────────────────────┘ │
│                             │                              │
│  ┌──────────────────────────┴───────────────────────────┐ │
│  │            SQLite + SQLAlchemy ORM                    │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | Python + Flask | 3.10+ / 3.x |
| ORM | SQLAlchemy | 2.x |
| Database | SQLite | 3.x |
| Analytics | Pandas + NumPy | 2.x / 1.26+ |
| Frontend | Bootstrap 5.3 + Chart.js 4.x | CDN |
| Auth | Flask-Login + Werkzeug | — |
| Testing | pytest | 8.x |

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

```bash
# 1. Clone or navigate to the project directory
cd PASS

# 2. Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate synthetic dataset (optional)
python generate_dataset.py

# 5. Initialize database and seed demo data
python run.py --seed

# 6. Start the development server
python run.py
```

### Demo Accounts

| Role | Username | Password |
|---|---|---|
| Instructor | `instructor` | `password123` |
| Student | `arjun` | `password123` |
| Admin | `admin` | `admin123` |

Open your browser and navigate to **http://127.0.0.1:5000**

---

## Project Structure

```
PASS/
├── run.py                      # Application entry point
├── app.py                      # Flask application factory
├── config.py                   # Configuration profiles (Dev/Test/Prod)
├── models.py                   # SQLAlchemy ORM models (7 tables)
├── requirements.txt            # Python dependencies
├── generate_dataset.py         # Synthetic data generator
│
├── engine/                     # Analytical Engine (Tier 2)
│   ├── __init__.py
│   ├── metrics.py              # MetricComputer (Δt, variance, trends)
│   ├── hysteresis.py           # HysteresisFilter (trend detection)
│   ├── credibility.py          # CredibilityScorer (weighted composite)
│   └── ingestion.py            # DataIngestor (CSV pipeline)
│
├── routes/                     # Flask Blueprints
│   ├── __init__.py
│   ├── auth.py                 # Authentication (login, register)
│   ├── dashboard.py            # Instructor dashboard
│   ├── student.py              # Student self-view
│   └── api.py                  # REST API endpoints
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Master layout (sidebar + navbar)
│   ├── auth/
│   │   ├── landing.html        # Public landing page
│   │   ├── login.html          # Login form
│   │   └── register.html       # Registration form
│   ├── dashboard/
│   │   ├── instructor.html     # Main dashboard with charts
│   │   ├── student_detail.html # Student drill-down view
│   │   └── upload.html         # CSV upload page
│   ├── student/
│   │   ├── self_view.html      # Student personal profile
│   │   └── no_profile.html     # No profile found page
│   └── errors/
│       ├── 403.html
│       ├── 404.html
│       └── 500.html
│
├── tests/                      # pytest Test Suite
│   ├── conftest.py             # Shared fixtures
│   ├── test_metrics.py         # MetricComputer tests
│   ├── test_hysteresis.py      # HysteresisFilter tests
│   ├── test_credibility.py     # CredibilityScorer tests
│   ├── test_ingestion.py       # DataIngestor tests
│   └── test_routes.py          # API & route integration tests
│
└── data/                       # Generated datasets (git-ignored)
    ├── submissions.csv
    └── test_submissions.csv
```

---

## Core Algorithms

### 1. Submission Velocity (Δt)

$$\Delta t = t_{deadline} - t_{submitted}$$

- **Positive**: Submitted early (seconds before deadline)
- **Negative**: Submitted late
- **Zero**: Submitted exactly at deadline

### 2. Variance Stability (Rolling σ)

$$\sigma_{pop} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (x_i - \bar{x})^2}$$

Computed over a rolling window (default: 5 submissions). High variance indicates erratic submission behavior.

### 3. Credibility Score (Weighted Composite)

$$C = 0.50 \cdot S_{\Delta t} + 0.30 \cdot S_{variance} + 0.20 \cdot S_{completion}$$

| Component | Weight | Range |
|---|---|---|
| Δt Score ($S_{\Delta t}$) | 50% | 0–100 |
| Variance Score ($S_{variance}$) | 30% | 0–100 |
| Completion Score ($S_{completion}$) | 20% | 0–100 |

### 4. Tier Classification

| Tier | Score Range | Action |
|---|---|---|
| **High** | ≥ 85 | Recognition + attendance waiver |
| **Medium** | 50–84 | Normal monitoring |
| **Low** | 30–49 | Increased attention |
| **Critical** | < 30 | Mandatory intervention |

### 5. Hysteresis Filter

- **Alert Trigger**: Monotonic decline over window size (default: 3)
- **Alert Resolution**: Requires 2 consecutive improvements (FR-09)
- Reduces false positive alerts by approximately **60%**

---

## API Documentation

### Public Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check |

### Authenticated Endpoints (Instructor)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/students` | List all students |
| GET | `/api/student/<id>` | Student detail + submissions |
| GET | `/api/dashboard/summary` | Dashboard statistics |
| GET | `/api/alerts` | Active alerts (filterable) |
| POST | `/api/ingest` | Upload CSV data |
| POST | `/api/policy/trigger` | Manual policy trigger |
| GET | `/api/export/csv` | Export data as CSV |

### Example Response: `/api/dashboard/summary`

```json
{
  "total_students": 30,
  "active_alerts": 8,
  "avg_credibility": 62.4,
  "at_risk_count": 5,
  "tier_distribution": {
    "high": 5,
    "medium": 15,
    "low": 7,
    "critical": 3
  }
}
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=engine --cov=routes --cov-report=html

# Run specific test module
pytest tests/test_metrics.py -v
pytest tests/test_credibility.py -v
```

### Test Coverage Target: ≥ 70% (NFR-07)

---

## Screenshots

> *Screenshots can be added after running the application*

1. **Instructor Dashboard** — KPI cards, alert feed, at-risk table, Δt trend chart
2. **Student Detail View** — Δt time-series, credibility breakdown radar, variance chart
3. **Student Self-View** — Credibility gauge, personal Δt trend, active perks
4. **CSV Upload** — Drag-and-drop upload with ingestion history
5. **Landing Page** — System overview with key metrics

---

## Success Criteria (from PRD)

| ID | Metric | Target |
|---|---|---|
| SC-01 | Early detection lead time | 4–6 weeks before grade penalties |
| SC-02 | Instructor decision latency reduction | ≥ 40% |
| SC-03 | False-positive alert rate | ≤ 15% over semester |
| SC-04 | Credibility vs. actual grade correlation | r ≥ 0.75 (pilot) |

---

## References

1. Baker, R. S., & Inventado, P. S. (2014). Educational Data Mining and Learning Analytics. *Springer*.
2. Romero, C., & Ventura, S. (2020). Educational Data Mining and Learning Analytics: An Updated Survey. *WIREs Data Mining and Knowledge Discovery*.
3. Essa, A., & Ayad, H. (2012). Improving Student Success Using Predictive Models and Data Visualisations. *Research in Learning Technology*.

---

## License

This project is developed as part of an academic thesis and is intended for educational purposes.

---

*Built with ❤️ for the Department of Computer Science & Engineering*
