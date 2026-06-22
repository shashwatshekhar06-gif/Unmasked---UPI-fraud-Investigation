# UNMASKED — Autonomous UPI Fraud Investigation System

UNMASKED takes a single fraud UPI ID and autonomously traces the entire money trail, maps every connected mule account, classifies the scam pattern, and generates a police-ready evidence report — in under 5 minutes.

UPI fraud hit ₹22,845 crore in India in 2024, with only a 6% recovery rate. The bottleneck isn't detection — banks already flag suspicious transactions. The problem is investigation speed. When money bounces through 3-5 mule accounts in minutes, manually tracing the chain across different banks takes 3-6 months. By then, the money is gone.

UNMASKED automates this entire investigation pipeline.

---

## How It Works

A victim submits the fraudster's UPI ID through the web interface. The system queues the case via Redis to a Python Celery worker, which runs a LangGraph multi-agent pipeline. Five AI agents work in sequence (with the first two running in parallel):

1. **Transaction Tracer** — walks the money chain hop by hop using BFS graph traversal
2. **Identity Intelligence** — scores every account for mule probability using a trained XGBoost model, with SHAP explainability for each prediction
3. **Scam Pattern Classifier** — matches the case against known fraud patterns using cosine similarity search over RBI/NPCI advisory embeddings (RAG)
4. **Network Expansion** — runs a 3-hop BFS traversal via PostgreSQL recursive CTEs to map the entire connected syndicate
5. **Report Generator** — produces a structured evidence document constrained to only cite verified facts

The React frontend renders the fraud network in real time using Cytoscape.js as agents complete, and generates a downloadable PDF evidence report with legal sections, SHAP explanations, and recommended actions.

---

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   React +   │────▶│  Spring Boot     │────▶│   Redis     │
│ Cytoscape.js│◀────│  REST + WebSocket│     │  Job Queue  │
└─────────────┘     └──────────────────┘     └──────┬──────┘
                                                     │
                                                     ▼
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│ PostgreSQL  │◀────│  Celery Worker   │◀────│  FastAPI    │
│ + pgvector  │────▶│  LangGraph 5     │     │  Endpoints  │
└─────────────┘     │  Agents          │     └─────────────┘
                    └──────────────────┘
```

Spring Boot and Python never call each other directly. Redis is the only coupling point — clean distributed systems design.

---

## Key Features

**Trained ML Classifier** — XGBoost model trained on transaction data from the VPA registry. 98.95% F1 score on the synthetic dataset (47 mules out of 1,379 accounts). Replaces hand-coded heuristics with a real learned model.

**SHAP Explainability** — Every flagged account comes with a human-readable breakdown of why it was flagged. "Extremely high fraud risk score on record", "Newly created account — a common mule account trait", "Receives and forwards funds in rapid succession." RBI compliance requires explainable decisions, not black boxes.

**Graph-Based Features** — Degree centrality, fan-out ratio, and cluster coefficient computed from the transaction network. Mule accounts are defined by their position in a network, not just individual attributes.

**Temporal Lifecycle Detection** — Mule accounts follow a lifecycle: created, dormant, burst of activity, abandoned. The system detects accounts in their "Active Burst" phase and flags them with activity concentration metrics and lifespan data.

**Live Fraud Network Visualization** — React + Cytoscape.js renders networks of 300+ nodes with depth-by-depth animation. Click any node to see risk score, bank, graph metrics, lifecycle phase, SHAP explanations, and flags.

**Alert Prioritization Dashboard** — Completed investigations ranked by a composite priority score (ML probability × network size × transaction volume). The most dangerous syndicates surface first.

**Analyst Feedback Loop** — Bank fraud analysts can confirm or reject mule classifications. Confirmed mules increase VPA risk scores; false positives decrease them. Accumulated feedback feeds into model retraining.

**RBI/NPCI Compliance Mapping** — Every alert maps to specific RBI circulars, NPCI advisories, IT Act sections, and IPC/BNS sections tied to the detected scam pattern. Legal standing for account freezes and auditor-ready documentation.

**PDF Evidence Reports** — Professional A4 reports with case overview, money trail analysis, high-risk accounts table, legal framework, confidence assessment, and recommended next steps. Designed to be attached to an FIR.

**Error Handling for Unknown VPAs** — If a submitted VPA hasn't been seen before, the system registers it for future intelligence linking and shows actionable guidance: file on cybercrime.gov.in, call 1930, contact your bank, preserve evidence.

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Layer | Java Spring Boot 3.2 | REST endpoints, WebSocket for live updates, Redis job dispatch |
| Agent Pipeline | Python, LangGraph, Celery | Multi-agent state machine, async task processing |
| ML Models | XGBoost, scikit-learn, SHAP | Mule account classification and explainability |
| Database | PostgreSQL + pgvector | Transaction storage, BFS via recursive CTEs, RAG embeddings |
| Message Queue | Redis | Async producer-consumer between Java and Python |
| Frontend | React, Cytoscape.js | Live fraud network graph, investigation dashboard |
| LLM | GPT-4o-mini (temp 0.1) | Constrained report generation, zero hallucination |
| PDF | ReportLab | Professional evidence report generation |

---

## Project Structure

```
unmasked/
├── unmasked-api/                    # Java Spring Boot
│   └── src/main/java/com/unmasked/api/
│       ├── CaseController.java      # REST endpoints
│       ├── CaseService.java         # Business logic + Redis dispatch
│       ├── WebSocketConfig.java     # STOMP over SockJS
│       └── RedisConfig.java         # Pub/sub → WebSocket bridge
│
├── unmasked-agents/                 # Python pipeline
│   ├── agents/agents.py             # 5 LangGraph agents + compliance mapping
│   ├── models/
│   │   ├── investigation_state.py   # LangGraph state with Annotated merge
│   │   ├── mule_classifier.pkl      # Trained XGBoost model
│   │   └── feature_names.json       # Feature metadata
│   ├── services/
│   │   ├── pipeline.py              # LangGraph StateGraph definition
│   │   ├── ml_model.py              # XGBoost + SHAP prediction
│   │   ├── celery_app.py            # Celery worker + queue consumer
│   │   ├── db.py                    # Database operations + graph metrics + temporal profiles
│   │   ├── embeddings.py            # pgvector cosine similarity search
│   │   ├── vpa_utils.py             # Mule confidence + ML prediction
│   │   ├── ws_emitter.py            # Redis pub/sub events
│   │   ├── pdf_report.py            # ReportLab PDF generation
│   │   ├── alert_queue.py           # Priority scoring
│   │   └── feedback.py              # Analyst verdict storage
│   ├── api/main.py                  # FastAPI endpoints
│   └── train_model.py               # Standalone model training script
│
├── unmasked-frontend/               # React + Vite
│   └── src/
│       ├── pages/
│       │   ├── Landing.jsx          # Home page
│       │   ├── Investigate.jsx      # Case submission + live graph
│       │   ├── CaseResults.jsx      # Results + graph + report + feedback
│       │   └── AlertDashboard.jsx   # Prioritized alert queue
│       └── components/
│           ├── Navbar.jsx
│           └── NetworkGraphBg.jsx
│
├── docker-compose.yml               # PostgreSQL + Redis containers
├── schema.sql                       # Database schema
├── generate_synthetic_data.py       # 500 fraud cases, 7 archetypes
├── seed_knowledge_base.py           # RBI/NPCI advisory embeddings
├── train_model.py                   # ML model training
└── requirements.txt                 # Python dependencies
```

---

## Setup and Installation

### Prerequisites
- Java JDK 21 (Adoptium)
- Python 3.12
- Node.js 18+
- Docker Desktop
- Maven 3.9+

### 1. Start the databases
```bash
cd unmasked
docker compose up -d
```

### 2. Set up environment
Copy `.env.example` to `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql://unmasked:unmasked@localhost:5432/unmasked
REDIS_URL=redis://localhost:6379/0
```

### 3. Install Python dependencies and train the model
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python generate_synthetic_data.py
python seed_knowledge_base.py
cd unmasked-agents
python train_model.py
```

### 4. Install frontend dependencies
```bash
cd unmasked-frontend
npm install
```

### 5. Run all services (5 terminals)

**Terminal 1 — Spring Boot API:**
```bash
cd unmasked-api
mvn spring-boot:run
```

**Terminal 2 — FastAPI + Agents:**
```bash
cd unmasked-agents
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**Terminal 3 — Celery Worker:**
```bash
cd unmasked-agents
celery -A services.celery_app worker --loglevel=info --pool=solo
```

**Terminal 4 — Frontend:**
```bash
cd unmasked-frontend
npm run dev
```

Open `http://localhost:3000`

---

## Demo

### Test VPAs from the synthetic dataset:

| VPA | Expected Result |
|-----|----------------|
| `rk_op05@ybl` | 311-node syndicate network, OLX Marketplace Scam, 62% confidence |
| `8873471434@ybl` | 233-node network, complete money trail with 10+ hops |
| `ashok_tiwari20@oksbi` | Medium network, KYC Phishing classification |

Submit any VPA with a unique transaction reference and an amount to start an investigation.

---

## ML Model Performance

Trained on 1,379 VPAs (47 mules / 1,332 legitimate) from the synthetic dataset:

| Metric | Score |
|--------|-------|
| Accuracy | 99.93% |
| Precision | 100% |
| Recall | 98% |
| F1 Score | 98.95% |

Class imbalance (3.4% positive rate) handled via XGBoost `scale_pos_weight`. Model saved as `models/mule_classifier.pkl`.

---

## Database Schema

- **cases** — fraud case submissions with status tracking
- **transactions** — hop-by-hop money trail with amounts and time deltas
- **vpa_registry** — VPA risk scores, flags, and case history (compounding data moat)
- **case_reports** — investigation results, graph JSON, report markdown
- **knowledge_base** — RBI/NPCI advisories with pgvector embeddings for RAG
- **analyst_feedback** — confirmed/rejected verdicts for model retraining

---

## Key Algorithms

**BFS Graph Traversal (PostgreSQL Recursive CTE):** Traces transaction chains up to 3 hops deep with cycle prevention. A single fraud VPA can expand to reveal networks of 300+ connected accounts.

**RAG Scam Classification:** Cosine similarity search over 1536-dimensional embeddings of RBI/NPCI advisories using pgvector's `<=>` operator. Matches incoming cases against known fraud patterns.

**SHAP TreeExplainer:** Per-prediction feature importance decomposition on the XGBoost model. Top contributing features returned in plain English for analyst review.

**Graph Metrics:** Degree centrality, fan-out ratio, and cluster coefficient computed in-memory from the BFS expansion result to identify hub nodes and syndicate structures.

---

## Built By

**Shashwat Shekhar**
B.Tech Computer Science, 2nd Year — VIT Vellore
- Email: shashwatshekhar06@gmail.com
- GitHub: [github.com/shashwatshekhar06-gif](https://github.com/shashwatshekhar06-gif)
- LinkedIn: [linkedin.com/in/shashwat-shekhar-5158451bb](https://linkedin.com/in/shashwat-shekhar-5158451bb)
