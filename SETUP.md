# FPL Scout — Local Setup Guide

Everything you need to run the full environment on a fresh machine.

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11 or 3.12 | https://python.org/downloads |
| Node.js | 18+ | https://nodejs.org |
| Docker Desktop | Latest | https://docker.com/products/docker-desktop |
| Git | Any | https://git-scm.com |

---

## 1 — Clone the Repo

```bash
git clone https://github.com/mow-1/FPL-Companion-.git fpl-scout
cd fpl-scout
```

---

## 2 — Start Database & Redis (Docker)

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL 16** on host port **5433**
- **Redis 7** on host port **6379**

Verify they're running:
```bash
docker ps
```

---

## 3 — Backend Setup

### 3a — Create & activate virtual environment

**Windows (PowerShell):**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Mac / Linux:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
```

### 3b — Install Python dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ **TensorFlow note**: if you're on Apple Silicon (M1/M2/M3), replace `tensorflow` with `tensorflow-macos` in requirements.txt before installing.

### 3c — Create the `.env` file

```bash
# Windows
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

The default values in `.env.example` work out-of-the-box with Docker. **No edits required** unless you want AI Advice (needs a Groq key — free at console.groq.com).

### 3d — Run database migrations

```bash
python manage.py migrate
```

### 3e — Start the Django backend

```bash
python manage.py runserver 8000
```

Keep this terminal open. Backend runs at **http://localhost:8000**

---

## 4 — Load FPL Data + Run All Predictions

Open a **new terminal**, activate the venv, then run these commands in order:

```bash
cd backend
# Windows: .\venv\Scripts\Activate.ps1
# Mac/Linux: source venv/bin/activate

# 1. Sync all players, teams, fixtures, gameweeks from the FPL API
python manage.py sync_fpl

# 2. Run ML predictions for the current gameweek (838 players)
python manage.py run_predictions

# 3. Sync official dream team data (GW1 → current)
python manage.py sync_dream_team

# 4. Backfill prediction history for all past gameweeks
python manage.py backfill_gw_history

# 5. Recalibrate adaptive scorer weights (improves accuracy)
python manage.py backfill_gw_history --recalibrate
```

Each command takes 10–60 seconds. After step 5, the GW history chart and track record are fully populated from **GW1 to the current gameweek**.

Expected output after step 5:
```
Avg |diff|: ~12 pts     GWs OK: 35+   Errors: 0
ScorerWeights.calibration_log: 35 entries saved.
```

---

## 5 — Frontend Setup

Open a **third terminal**:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

---

## 6 — Open the App

Visit **http://localhost:5173** in your browser.

### Test Account

| Field | Value |
|-------|-------|
| Email | `test@fpl.com` |
| Password | `FPLScout2026!` |
| FPL Team ID | `10357619` |

This account is pre-loaded in the database. After logging in, click **Sync Squad** on the Dashboard to pull live FPL data for the linked team.

You can also register a new account and enter your own FPL Team ID (found in the URL on the official FPL website under the Points tab).

---

## 7 — Full Stack at a Glance

```
http://localhost:5173   ← React frontend (Vite)
http://localhost:8000   ← Django REST API
localhost:5433          ← PostgreSQL (via Docker)
localhost:6379          ← Redis (via Docker)
```

---

## Restart After a Reboot

```powershell
# 1. Start containers
docker-compose up -d

# 2. Backend (activate venv first)
cd backend
.\venv\Scripts\Activate.ps1   # Windows
python manage.py runserver 8000

# 3. Frontend (new terminal)
cd frontend
npm run dev
```

---

## ML Models

The trained models live in `backend/ml_artifacts/`. Each position has multiple architectures:

| Directory | Position | Architecture |
|-----------|----------|-------------|
| `GK_lstm_base/` | Goalkeeper | LSTM |
| `GK_gru_enhanced/` | Goalkeeper | GRU |
| `GK_lstm_enhanced/` | Goalkeeper | LSTM (enhanced features) |
| `DEF_gru_enhanced/` | Defender | GRU |
| `DEF_lstm_enhanced/` | Defender | LSTM |
| `DEF_tft_enhanced/` | Defender | Temporal Fusion |
| `MID_lstm_base/` | Midfielder | LSTM |
| `MID_ensemble_base/` | Midfielder | Ensemble |
| `MID_tft_enhanced/` | Midfielder | Temporal Fusion |
| `FWD_gru_base/` | Forward | GRU |

Each directory contains `model.keras` + `scaler.pkl`. Best model per position is selected automatically by `ml_loader.py`.

---

## Troubleshooting

**`SSL: CERTIFICATE_VERIFY_FAILED` on sync_fpl**
Already fixed in `fpl_api.py` (`verify=False`). If it reappears, ensure you're using the repo version of the file.

**`django.db.OperationalError: could not connect to server`**
Docker containers aren't running. Run `docker-compose up -d` and check `docker ps`.

**Port 5433 already in use**
Another service is on 5433. Change the left side of the docker-compose port mapping: `"5434:5432"` and set `DB_PORT=5434` in `.env`.

**`ModuleNotFoundError: No module named 'tensorflow'`**
Run `pip install -r requirements.txt` with the venv activated.

**Frontend 404 on API calls**
Make sure Django is running on port 8000. Vite proxies `/api/*` to `http://localhost:8000`.

---

## Updating Predictions Each Gameweek

After each GW deadline, run:
```bash
python manage.py sync_fpl          # pull new player statuses
python manage.py run_predictions   # regenerate predictions
```

After results are published:
```bash
python manage.py sync_dream_team
python manage.py backfill_gw_history --recalibrate
```
