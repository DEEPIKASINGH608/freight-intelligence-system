# Freight Intelligence System

> **Domain:** Transportation & Logistics / Supply Chain  
> **Category:** Software  
> **Philosophy:** Don't just predict the freight rate. Turn the prediction into an operational decision.

---

## Executive Summary

The Freight Intelligence System is an end-to-end decision-support platform that transforms raw freight data into actionable maritime chartering recommendations. Rather than acting purely as a predictive model or dashboard, the system layers risk assessment, physical operational constraints, optimization solvers, and financial exposure calculations onto machine-learning forecasts to guide chartering decisions.

---

## Core Value Proposition & Workflow

The system progresses across an end-to-end operational pipeline:
DATA ──> FORECAST ──> RISK ──> CONSTRAINTS ──> OPTIMIZATION ──> FINANCIAL EXPOSURE ──> DECISION

### Decision Engine Outputs
* **`CHARTER NOW`**: Optimal time to lock in freight contracts.
* **`WAIT`**: Favorable conditions expected to improve; delay chartering.
* **`WATCH`**: High market activity; monitoring required.
* **`WATCH — CHARTER BLOCKED`**: Issued when freight rates are expected to rise sharply, but no candidate vessel satisfies physical/operational constraints.

---

## Demonstration Scenario Overview

A representative demonstration scenario simulates a major bulk shipping route:

| Parameter | Specification Details |
| :--- | :--- |
| **Cargo Details** | 75,000 tons of Iron Ore *(Sample scenario: 95,000 tons)* |
| **Route & Distance** | Australia (Port Hedland) → Paradip, India (~3,850 nautical miles) |
| **Timeline / Deadline** | 30-day delivery deadline *(Sample scenario: 40 days)* |
| **Current Spot Freight Rate** | **$22.50 / ton** *(Sample scenario: $25.00 / ton)* |
| **30-Day AI Forecast Rate** | **$42.76 / ton** (+90.0% increase) *(Sample scenario: $41.96 / ton, +67.8%)* |
| **90% Prediction Interval** | **$38.97 – $46.59 / ton** |
| **Financial Exposure (Delta)** | Book Now: **₹14.01 Cr** vs. Wait 30 Days: **₹26.62 Cr** (Exposure Delta: **₹12.61 Cr**) |
| **Risk Score & Level** | **45.4 / 100 (MEDIUM Risk)** *(Sample scenario: 64.9, MEDIUM)* |
| **Selected Feasible Vessel** | **MV Iron Pioneer (Panamax)**, Operational time: ~28.7 days *(Sample: MV Eastern Trader, Capesize, ~32.3 days)* |
| **Recommended Action** | **CHARTER NOW** |

---

## Core System Architecture & Solvers

### Risk Assessment Engine
Calculates composite operational risk based on input criteria:
* **0.00 – 39.99**: LOW Risk
* **40.00 – 69.99**: MEDIUM Risk
* **70.00 – 100.00**: HIGH Risk

### Port & Vessel Optimization Solver
Filters out infeasible vessels against physical and time parameters:
* Cargo quantity vs. Vessel capacity
* Maximum allowed draft & beam
* Origin/Destination port compatibility
* Vessel availability, ETA, and strict delivery deadlines
* Operational duration and cost efficiency

### Procurement Optimization Solver
Allocates cargo across multi-supplier configurations using **SciPy HiGHS Linear Programming** subject to:
* Individual supplier capacities
* Minimum order quantities (MOQ)
* Maximum allocation percentages
* Landed and freight cost structures
* Total required cargo quantities

### Financial Exposure Calculation
Calculates cost comparative bounds:
* **Book Now** = cargo quantity × current freight rate
* **Wait** = cargo quantity × forecast freight rate

---

## Machine Learning & Data Pipeline

### Data Strategy
The system processes data across key categories aligned with industry requirements:
* Historical freight rates
* Bunker fuel prices
* Cargo demand & vessel availability
* Port congestion & seasonality trends
* Operational and commodity indicators

### ML Workflow
```text
PostgreSQL Data Extraction
          │
          ▼
SQLAlchemy ORM (FreightRate Model)
          │
          ▼
Pandas DataFrame Data Pipeline
          │  ├── Date conversion & chronological sorting
          │  ├── Target generation: shift(-30) for 30-observation horizon
          │  ├── Lag features & rolling statistics
          │  └── Cyclical seasonality encoding & missing value handling
          │
          ▼
Processed Dataset (processed/freight_features_processed.csv)
          │
          ▼
Chronological Train / Test Split
          │
          ▼
Multi-Model Evaluation Benchmarking
  [ Naive | Linear Regression | Random Forest | XGBoost ]
          │  (Evaluated via MAE + RMSE)
          ▼
Selected Production Model: Random Forest
          │
          ▼
Serialized Artifact: models/forecaster_model.pkl

### `Technical Architecture & Directory Structure`

freight-intelligence-system/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/
│   │   │   ├── decision.py
│   │   │   ├── forecast.py
│   │   │   ├── optimization.py
│   │   │   ├── risk.py
│   │   │   ├── routes.py
│   │   │   └── vessels.py
│   │   ├── core/config.py
│   │   ├── data/vessel_fleet.json
│   │   ├── database/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── ml/
│   │   │   ├── explainability.py
│   │   │   ├── predict_forecaster.py
│   │   │   ├── risk_engine.py
│   │   │   └── train_forecaster.py
│   │   ├── models/
│   │   │   ├── decision.py
│   │   │   ├── freight_rate.py
│   │   │   ├── route.py
│   │   │   └── vessel.py
│   │   ├── optimization/
│   │   │   ├── port_constraints.py
│   │   │   ├── procurement_solver.py
│   │   │   └── vessel_solver.py
│   │   ├── schemas/
│   │   ├── services/decision_engine.py
│   │   └── main.py
│   ├── .env.example
│   └── requirements.txt
├── data/
│   ├── processed/freight_features_processed.csv
│   └── raw/historical_freight_raw.csv
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── charts/FreightForecastChart.jsx
│   │   │   └── common/
│   │   │       ├── KPICard.jsx
│   │   │       ├── Navbar.jsx
│   │   │       └── RiskBadge.jsx
│   │   ├── pages/CommandCenter.jsx
│   │   ├── services/api.js
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── models/
│   │   ├── forecaster_model.pkl
│   │   └── forecaster_scaler.pkl
│   └── scripts/
│       ├── evaluate_models.py
│       ├── generate_synthetic_data.py
│       ├── seed_database.py
│       ├── train_model.py
│       └── validate_data.py
└── .gitignore

Technology Stack
* **Backend Framework:** Python, FastAPI

Database & ORM: PostgreSQL, SQLAlchemy

Data Science & ML: Pandas, NumPy, scikit-learn, XGBoost, joblib

Optimization Solver: SciPy HiGHS

Frontend UI: React, Vite, JavaScript, Tailwind CSS, Axios

Version Control & Deployment: Git/GitHub, Render (Backend), Vercel (Frontend)

API Documentation
FastAPI interactive documentation is accessible at /docs.
Method Endpoint Description 
POST/api/v1/decision/evaluateEvaluates complete decision engine pipelinePOST/api/v1/forecast/predictGenerates freight rate forecast predictionsPOST/api/v1/risk/evaluateCalculates operational risk assessment scorePOST/api/v1/optimize/vesselsComputes vessel matching and constraint feasibilityPOST/api/v1/optimize/procurementComputes multi-supplier procurement optimizationGET/api/v1/routesFetches available marine shipping routesGET/api/v1/vesselsFetches active vessel information

Getting Started
Local Setup
1. Repository Setup

git clone https://github.com/DEEPIKASINGH608/freight-intelligence-system.git
cd freight-intelligence-system

2. Backend Installation & Server Run
# Set up virtual environment
python -m venv venv
venv\Scripts\Activate.ps1

# Install dependencies and launch FastAPI server
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

Local Backend Endpoint: http://localhost:8000

Swagger API Documentation: http://localhost:8000/docs

3. Frontend Installation & Setup
Open a separate terminal window:

cd frontend
npm install
npm run dev

Configure local environment (frontend/.env):
VITE_API_BASE_URL=http://localhost:8000/api/v1

Deployment Configuration
#Backend Deployment (Render)
-> Root Directory: backend
-> Build Command: pip install -r requirements.txt
->Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT

#Frontend Deployment (Vercel)
-> Root Directory: frontend
-> Install Command: npm install
-> Build Command: npm run build
-> Output Directory: dist

#Production API Variable:
Code snippet
VITE_API_BASE_URL=https://freight-intelligence-backend.onrender.com/api/v1

Security Practices
Keep environment variables local: Ensure backend/.env and frontend/.env are never committed to source control.

Commit template files: Only commit .env.example templates.

Configured .gitignore:

venv/
__pycache__/
*.pyc
.env

Limitations & Future Scope
Prototype Limitations
What-if scenario inputs utilize synthetic/controlled simulation datasets.

Prototype does not claim access to proprietary market data.

Current dataset volume is smaller than commercial platforms.

Target shift horizon uses 30 observations/rows rather than strictly calendar-enforced days.

Model performance can shift when market regimes change.

The 90% prediction interval is an empirical uncertainty estimate, not an absolute price guarantee.

Planned Roadmap Extensions
Live freight-market integration feeds

Real-time AIS vessel tracking and port congestion monitors

Real-time bunker fuel and commodity indicators

Marine weather and sea-condition feeds

Automated model retraining, drift-detection, and probabilistic forecasting

Multi-voyage charter planning and short/medium-term contract optimization

Production-grade authentication and role-based access control (RBAC)