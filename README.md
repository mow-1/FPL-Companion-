<div align="center">

# FPL Manager Assistant

### AI-Powered Fantasy Premier League Decision Support System

*Graduation Project — Computer Science*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.0-092E20?style=flat&logo=django&logoColor=white)](https://djangoproject.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15-FF6F00?style=flat&logo=tensorflow&logoColor=white)](https://tensorflow.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)

> A full-stack web application that uses deep learning models trained on a decade of Premier League data to deliver weekly captain picks, transfer recommendations, and squad optimisation for Fantasy Premier League managers.

</div>

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Key Features](#2-key-features)
3. [System Architecture](#3-system-architecture)
4. [Machine Learning Models](#4-machine-learning-models)
5. [Prediction Pipeline](#5-prediction-pipeline)
6. [Tech Stack](#6-tech-stack)
7. [Project Structure](#7-project-structure)
8. [Getting Started](#8-getting-started)
9. [API Reference](#9-api-reference)
10. [Performance Results](#10-performance-results)
11. [Screenshots](#11-screenshots)

---

## 1. Project Overview

Fantasy Premier League (FPL) is one of the world's largest online games with over 11 million active managers per season. Every gameweek, managers must make high-stakes decisions — which player to captain, whether to transfer, and how to optimise their squad — with limited time and imperfect information.

This project builds an end-to-end decision support system that:

- **Trains deep learning models** (LSTM, GRU, Temporal Fusion Transformer, Ensemble) on 10 seasons of Premier League data (2016–17 to 2025–26) to predict player points per gameweek
- **Exposes predictions via a REST API** built on Django REST Framework with JWT authentication
- **Delivers actionable weekly advice** through a modern React dashboard — captain picks, transfer suggestions, best squad builder, fixture difficulty planning, and chip strategy
- **Learns continuously** — an adaptive scorer recalibrates its weights after each completed gameweek, improving recommendations over the course of a season

The system is designed as a complete production-grade application: containerised infrastructure, asynchronous task processing, live FPL API synchronisation, and a responsive single-page frontend.

---

## 2. Key Features

### For the Manager
| Feature | Description |
|---|---|
| **Captain Picks** | Weekly captain and vice-captain recommendations with a differential (low-ownership) alternative |
| **Transfer Suggestions** | Ranked transfer targets considering form, fixtures, price, and ownership |
| **Squad Builder** | Optimal 15-player squad within a £100m budget using linear optimisation |
| **Live Squad Sync** | One-click sync with your real FPL team via your Team ID |
| **Fixture Planner** | Colour-coded fixture difficulty calendar for planning weeks ahead |
| **Weekly Results** | Historical predicted vs actual points tracking with formation breakdown |
| **Player Explorer** | Full player database with live stats, form, and price history |
| **Chip Advisor** | Gameweek-specific chip (Wildcard, Free Hit, Bench Boost, Triple Captain) recommendations |
| **Differential Finder** | Low-ownership high-upside picks ranked by value score |
| **Community Compare** | Model picks vs community consensus — where the AI disagrees with the crowd |

### For the System
| Feature | Description |
|---|---|
| **Multi-model ensemble** | LSTM + XGBoost blend outperforms any single model |
| **Adaptive calibration** | Scorer weights update after every finished gameweek |
| **Two-tier feature sets** | Base (10 seasons) and Enhanced (4 seasons + expected stats) pipelines |
| **Position-specific models** | Separate models trained per position (GK/DEF/MID/FWD) |
| **Anti-leakage design** | All rolling features use `shift(1)` — no future data contamination |
| **Blank-rate penalty** | High-variance players (boom/bust) are penalised in squad selection |
| **Club diversity constraint** | Maximum 3 players per club enforced across all squad builders |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                          │
│              React 18 + Vite + Tailwind CSS + React Query        │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS / REST
┌──────────────────────────────▼──────────────────────────────────┐
│                     DJANGO REST FRAMEWORK                        │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ accounts │  │   fpl    │  │ predictions │  │   manager   │  │
│  │  /auth/  │  │  /fpl/   │  │/predictions/│  │  /manager/  │  │
│  │  JWT     │  │  Sync    │  │  ML Layer   │  │  Squad/     │  │
│  │  OAuth   │  │  FPL API │  │  Optimizer  │  │  Transfers  │  │
│  └──────────┘  └──────────┘  └─────────────┘  └─────────────┘  │
│                                    │                             │
│  ┌─────────────────────────────────▼───────────────────────────┐│
│  │              CELERY WORKERS (Async Tasks)                    ││
│  │  • Periodic FPL data sync (players, fixtures, gameweeks)    ││
│  │  • Batch prediction runs after data sync                    ││
│  │  • Post-GW calibration of scorer weights                    ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼───────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │   PostgreSQL 16  │ │  Redis 7    │ │ ML Artifacts │
    │   Primary DB     │ │  Broker +   │ │ .keras/.pkl  │
    │                  │ │  Cache      │ │  per position│
    └──────────────────┘ └─────────────┘ └─────────────┘
```

### Data Flow

```
FPL Official API ──► sync_fpl (Celery) ──► PostgreSQL
                                              │
                                     ┌────────▼────────┐
                                     │  ml_loader.py   │
                                     │  Loads trained  │
                                     │  LSTM/GRU/TFT   │
                                     │  models         │
                                     └────────┬────────┘
                                              │
                                     ┌────────▼────────┐
                                     │ scorer_weights  │
                                     │  Adaptive post- │
                                     │  processing +   │
                                     │  calibration    │
                                     └────────┬────────┘
                                              │
                                     ┌────────▼────────┐
                                     │  optimizer.py   │
                                     │  Best squad     │
                                     │  selection      │
                                     └────────┬────────┘
                                              │
                                         REST API
                                              │
                                        React UI
```

---

## 4. Machine Learning Models

### Model Architecture

Four model architectures are trained and evaluated for each position:

| Model | Architecture | Key Design |
|---|---|---|
| **LSTM** | 2-layer LSTM (128→64 units) + Dropout(0.3) + Dense | Captures long-range temporal dependencies in form sequences |
| **GRU** | 2-layer GRU (128→64 units) + Dropout(0.3) + Dense | Faster convergence than LSTM, fewer parameters |
| **TFT** | Temporal Fusion Transformer with multi-head attention | Interpretable attention weights over past gameweeks |
| **Ensemble** | LSTM predictions + XGBoost meta-learner | Blends neural and gradient-boosted predictions |

All models use:
- **Sequence length**: 5 gameweeks (sliding window input)
- **Target**: `total_points` for the next gameweek
- **Scaling**: `StandardScaler` fitted on training data only
- **Loss**: Mean Squared Error
- **Optimiser**: Adam (lr=0.001, with ReduceLROnPlateau)

### Two-Tier Feature Strategy

| Tier | Seasons | Rows | Features | Notes |
|---|---|---|---|---|
| **Base** | 2016–17 → 2025–26 | ~206,000 | 52–55 per position | Maximum training data |
| **Enhanced** | 2022–23 → 2025–26 | ~83,000 | +5 expected stats | xG, xA, xGI, xP, xGC added |

### Temporal Train / Validation / Test Split

```
Train    ──────────────────────────────────────── Validation ── Test
2016-17  2017-18  2018-19  2019-20  2020-21  2021-22  2022-23  2023-24 │ 2024-25 │ 2025-26
─────────────────────────────────────────────────────────────────────────────────────────
         8 seasons of training data (no future leakage)         │  held  │  held
```

### Performance Results (2024–25 Validation Season)

| Position | Best Model | MAE | Within ±2 pts | R² |
|---|---|---|---|---|
| **GK** | Ensemble Base | **0.600** | **91.9%** | 0.335 |
| **DEF** | Ensemble Base | **0.867** | **89.3%** | 0.168 |
| **MID** | LSTM Base | **0.909** | **90.8%** | 0.194 |
| **FWD** | GRU Base | **0.949** | **88.2%** | 0.261 |
| **Average** | — | **0.842** | **90.1%** | — |

> **Within ±2 pts** is the primary evaluation metric — it measures what fraction of predictions land within 2 FPL points of the actual score, which is the threshold relevant for real captain and transfer decisions.

---

## 5. Prediction Pipeline

### Feature Engineering (52–60 features per player per GW)

**Rolling Form Features**
```
total_points_L3, total_points_L5       # 3 and 5-GW rolling average points
goals_scored_L3, assists_L5            # Offensive contribution trends
clean_sheets_L3 (GK/DEF)              # Defensive contribution trends
saves_L5 (GK)                          # Goalkeeper-specific
bonus_L3, bps_L5                       # Bonus point system indicators
```

**Engineered Features**
```
form_L3     = sum of last 3 GW points
momentum    = 0.6 × L3_avg + 0.4 × L5_avg
form_trend  = L3_avg − L5_avg         (improving or declining?)
consistency = std dev of last 5 scores
home_form   = was_home × form_L3
```

**Opponent Difficulty**
```
opp_strength_overall                  # From FPL team strength ratings
opp_dynamic_fdr                       # Rolling xGC ratio (recent defensive form)
strength_diff                         # Player's team vs opponent differential
```

**Ceiling / Variance Features**
```
haul_rate_L10    # Fraction of last 10 GWs with ≥10 pts (big-score probability)
max_pts_L5       # Best score in last 5 GWs (ceiling proxy)
pts_variance_L10 # Volatility — boom/bust indicator
bonus_rate_L10   # Consistency of bonus point appearances
```

**Expected Stats (Enhanced Tier)**
```
expected_goals, expected_assists       # From FPL official xStats
expected_goal_involvements (xGI)
expected_goals_conceded (xGC — GK/DEF)
xP (FPL expected points)
```

### Adaptive Scoring Layer

After each finished gameweek, `calibrate_after_gw()` analyses per-player prediction errors and adjusts 14 learnable weights — including form/PPG blend ratio, position-specific bonus multipliers, and a global calibration scalar — within strict bounds to prevent overfitting. The system accumulates a calibration log across all 38 gameweeks.

### Squad Optimisation

The `build_best_team()` function runs a two-phase greedy optimisation:

1. **Phase 1 — XI Selection**: For each valid formation (3-4-3, 4-3-3, 4-4-2, etc.), reserve the minimum bench cost then allocate the remaining budget to the highest-predicted XI. The formation that maximises captain-weighted predicted points wins.

2. **Phase 2 — Bench Fill**: Fill the remaining 4 bench slots with the cheapest legal players, respecting the 3-players-per-club constraint.

Additional constraints enforced during optimisation:
- Blank-rate penalty on boom/bust players (>50% non-scoring GWs)
- DEF same-team correlation penalty (3rd+ DEF from same club gets ×0.92)
- FDR-adjusted captain scoring (easy fixture: ×1.15, hard fixture: ×0.75)

---

## 6. Tech Stack

### Backend
| Library | Version | Purpose |
|---|---|---|
| Django | 5.0 | Web framework & ORM |
| Django REST Framework | 3.15 | REST API |
| SimpleJWT | 5.3 | JWT authentication |
| django-allauth | 64.0 | Google OAuth |
| Celery | 5.4 | Async task queue |
| django-celery-beat | 2.6 | Periodic task scheduling |
| TensorFlow / Keras | 2.15 | LSTM, GRU, TFT models |
| XGBoost | 2.0 | Ensemble meta-learner |
| scikit-learn | 1.4 | Preprocessing & evaluation |
| pandas / numpy | 2.2 / 1.26 | Data processing |
| PuLP | 2.7 | Linear programming (squad optimisation) |
| Groq | 0.9 | LLM reasoning layer for advice |
| psycopg2 | 2.9 | PostgreSQL adapter |
| gunicorn | 22.0 | Production WSGI server |

### Frontend
| Library | Version | Purpose |
|---|---|---|
| React | 18 | UI framework |
| Vite | 5 | Build tool & dev server |
| Tailwind CSS | 3 | Utility-first styling |
| React Query | 5 | Server state management & caching |
| React Router | 6 | Client-side routing |
| Axios | 1.7 | HTTP client |
| Recharts | 2.12 | Data visualisation (charts) |
| Framer Motion | 11 | Animations |
| Lucide React | — | Icon library |

### Infrastructure
| Service | Version | Purpose |
|---|---|---|
| PostgreSQL | 16 | Primary relational database |
| Redis | 7 | Celery message broker & result backend |
| Docker Compose | — | Local development orchestration |

---

## 7. Project Structure

```
fpl-manager-assistant/
│
├── backend/                        # Django application
│   ├── config/                     # Project settings, URLs, Celery, auth
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── celery.py
│   │   └── auth.py                 # Lenient JWT authenticator
│   │
│   ├── accounts/                   # User authentication
│   │   ├── models.py               # Custom user model
│   │   ├── views.py                # Register, login, profile, OAuth
│   │   └── urls.py
│   │
│   ├── fpl/                        # FPL data layer
│   │   ├── models.py               # Team, Player, Gameweek, Fixture, PlayerGameweekStats
│   │   ├── fpl_api.py              # FPL official API client
│   │   ├── sync.py                 # Full data synchronisation logic
│   │   ├── tasks.py                # Celery periodic sync tasks
│   │   └── management/commands/sync_fpl.py
│   │
│   ├── predictions/                # ML prediction layer
│   │   ├── models.py               # Prediction, BestPickRecommendation, ScorerWeights
│   │   ├── ml_loader.py            # Load trained models, run inference
│   │   ├── scorer_weights.py       # Adaptive weight calibration
│   │   ├── optimizer.py            # Squad optimisation (best team, past team)
│   │   ├── views.py                # Prediction API endpoints
│   │   └── tasks.py                # Celery prediction tasks
│   │
│   ├── manager/                    # User squad management
│   │   ├── models.py               # Squad, SquadPlayer, TransferSuggestion, CaptainSuggestion
│   │   ├── advisor.py              # Transfer & captain recommendation engine
│   │   ├── optimizer.py            # User-specific squad optimiser
│   │   └── views.py                # Dashboard, sync, transfers, captain, chips
│   │
│   └── requirements.txt
│
├── frontend/                       # React application
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Landing.jsx         # Public marketing page
│   │   │   ├── Dashboard.jsx       # Squad pitch, captain, transfers overview
│   │   │   ├── Predictions.jsx     # Best team, track record, GW history charts
│   │   │   ├── MyTeam.jsx          # Synced squad management
│   │   │   ├── Advice.jsx          # Full AI advice (transfers, chips, best XI)
│   │   │   ├── Players.jsx         # Player browser with stats & filters
│   │   │   ├── Fixtures.jsx        # Fixture difficulty calendar
│   │   │   ├── Profile.jsx         # User settings & FPL ID linking
│   │   │   ├── Login.jsx
│   │   │   └── Register.jsx
│   │   │
│   │   ├── components/
│   │   │   ├── Layout.jsx          # App shell, sidebar navigation
│   │   │   ├── PlayerPhoto.jsx     # FPL player photo component
│   │   │   └── PitchSVG.jsx        # Football pitch background SVG
│   │   │
│   │   ├── api/
│   │   │   ├── client.js           # Axios instance + JWT interceptors
│   │   │   └── fpl.js              # All API call functions
│   │   │
│   │   ├── context/
│   │   │   ├── AuthContext.jsx     # Global auth state
│   │   │   └── ThemeContext.jsx    # Dark/light mode
│   │   │
│   │   └── theme/teamColors.js     # Premier League team colour palette
│   │
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── docs/                           # Research & test reports
│   ├── xi_quality_improvements.md  # Layer-by-layer optimiser impact analysis
│   ├── xi_quality_test_report.md
│   └── test_fixes_results.md
│
├── docker-compose.yml              # PostgreSQL + Redis services
├── .env.example                    # Environment variable template
└── README.md
```

---

## 8. Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop (for PostgreSQL and Redis)
- A trained ML model artifacts directory (see [ML Artifacts](#ml-artifacts))

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/fpl-manager-assistant.git
cd fpl-manager-assistant
```

### 2. Start Infrastructure

```bash
docker-compose up -d
```

This starts PostgreSQL (port 5433) and Redis (port 6379).

### 3. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY, DB credentials, REDIS_URL

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Sync FPL data (players, teams, gameweeks, fixtures)
python manage.py sync_fpl

# Run predictions for the current gameweek
python manage.py run_predictions

# Start development server
python manage.py runserver
```

### 4. Start Celery Worker (optional, for background tasks)

```bash
# In a separate terminal, from the backend/ directory
celery -A config worker -l info
celery -A config beat -l info     # For periodic sync
```

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at **http://localhost:5173**

### 6. Environment Variables

```env
# backend/.env

SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (matches docker-compose defaults)
DB_NAME=fpl_manager
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5433

# Redis
REDIS_URL=redis://localhost:6379/0

# Frontend (CORS)
FRONTEND_URL=http://localhost:5173

# Google OAuth (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# ML artifacts path
ML_ARTIFACTS_PATH=ml_artifacts

# Groq LLM (optional — for AI reasoning layer)
GROQ_API_KEY=
```

### ML Artifacts

The trained model files (`.keras` and `.pkl`) are not included in the repository due to size. Place your trained models in the following structure:

```
backend/ml_artifacts/
├── GK_lstm_base/
│   ├── model.keras
│   └── scaler.pkl
├── GK_gru_base/
├── GK_ensemble_base/
├── DEF_lstm_base/
├── DEF_gru_enhanced/
├── MID_lstm_base/
├── MID_ensemble_base/
├── FWD_gru_base/
└── ...
```

Models can be trained using the pipeline in the companion repository: [fpl-rnn-models](https://github.com/YOUR_USERNAME/fpl-rnn-models) *(link the RNN training repo here)*.

---

## 9. API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register/` | Register a new account |
| `POST` | `/api/auth/login/` | Obtain JWT access + refresh tokens |
| `POST` | `/api/auth/token/refresh/` | Refresh access token |
| `POST` | `/api/auth/logout/` | Blacklist refresh token |
| `GET/PATCH` | `/api/auth/profile/` | Get or update user profile |

### FPL Data

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/fpl/players/` | All players with stats (filterable, paginated) |
| `GET` | `/api/fpl/players/{fpl_id}/` | Single player detail |
| `GET` | `/api/fpl/teams/` | All Premier League teams |
| `GET` | `/api/fpl/gameweeks/` | All gameweeks |
| `GET` | `/api/fpl/gameweeks/current/` | Current/next gameweek |
| `GET` | `/api/fpl/fixtures/` | Fixtures (filterable by GW, team) |

### Predictions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/predictions/` | All predictions for current GW |
| `GET` | `/api/predictions/best-picks/` | Top predicted players by position |
| `GET` | `/api/predictions/best-team/` | Optimal 15-player squad |
| `GET` | `/api/predictions/track-record/` | Historical predicted vs actual squads |
| `GET` | `/api/predictions/gw-history/` | Per-GW summary statistics |
| `GET` | `/api/predictions/differentials/` | Low-ownership high-value picks |
| `GET` | `/api/predictions/community-compare/` | Model vs community consensus |

### Manager (Authenticated)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/manager/dashboard/` | Squad snapshot + suggestions |
| `POST` | `/api/manager/squad/sync/` | Sync squad from FPL API |
| `GET` | `/api/manager/transfers/` | Saved transfer suggestions |
| `POST` | `/api/manager/transfers/` | Generate new transfer suggestions |
| `GET/POST` | `/api/manager/captain/` | Get or generate captain advice |
| `GET` | `/api/manager/chips/` | Chip usage recommendations |
| `GET/POST` | `/api/manager/advice/` | Full AI gameweek advice |

---

## 10. Performance Results

### Model Accuracy (2024–25 Validation Season)

```
Position │ Model          │   MAE  │ Within ±2pts │  RMSE  │   R²
─────────┼────────────────┼────────┼──────────────┼────────┼───────
GK       │ Ensemble Base  │  0.600 │    91.9%     │  1.612 │ 0.335
DEF      │ Ensemble Base  │  0.867 │    89.3%     │  2.051 │ 0.168
MID      │ LSTM Base      │  0.909 │    90.8%     │  2.184 │ 0.194
FWD      │ GRU Base       │  0.949 │    88.2%     │  2.317 │ 0.261
─────────┼────────────────┼────────┼──────────────┼────────┼───────
Average  │ —              │  0.842 │    90.1%     │  2.041 │  —
```

### Adaptive Scoring Simulation (GW1–29, 2024–25)

The adaptive scorer was simulated across 29 gameweeks, building the best predicted team each week and comparing it to actual outcomes:

```
GW Range │ Avg │Predicted − Actual│
─────────┼────────────────────────
GW 1–10  │         13.4 pts
GW 11–20 │         17.1 pts
GW 21–29 │         20.9 pts
```

> The increasing gap in later gameweeks is primarily driven by captain selection variance — when the captain (often Haaland, recommended by ~90% of weeks) blanks, the average difference spikes to −23 pts vs −7 pts when the captain scores.

### Base vs Enhanced Models

The Enhanced tier (with expected stats) uses 4× fewer training seasons. Results show:

- Enhanced models match base model accuracy for MID/FWD (where xG/xA are most informative)
- Base models outperform for GK/DEF (more training seasons outweigh expected stats signal)
- Best production models use a mix: **Enhanced for MID/FWD, Base for GK/DEF**

---

## 11. Screenshots

> *(Add screenshots of the key pages here)*

| Dashboard | Predictions |
|---|---|
| *Squad pitch with captain/VC, KPI cards, transfer panel* | *Best XI on pitch, track record charts, GW history* |

| Players | Fixtures |
|---|---|
| *Full player browser with position filters and stats* | *Colour-coded difficulty calendar* |

---

## Acknowledgements

- **FPL Data**: [Fantasy Premier League Official API](https://fantasy.premierleague.com/api/)
- **Historical Data**: [vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League) — 10 seasons of cleaned FPL data
- **Expected Stats**: FPL in-built xG/xA metrics (2022–23 onwards)

---

## License

This project was developed as a graduation thesis. All rights reserved.

---

<div align="center">
<sub>Built with Django · React · TensorFlow · trained on a decade of Premier League data</sub>
</div>
