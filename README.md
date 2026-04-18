# ⚔️ AI Dungeon Master

> An intelligent, full-stack Dungeons & Dragons companion powered by **Groq LLaMA-3.3-70B**, featuring a multi-agent AI pipeline, semantic RAG memory, and real-time streaming over WebSockets.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-ai--dungeon--master--coral.vercel.app-64ffda?style=for-the-badge&logo=vercel)](https://ai-dungeon-master-coral.vercel.app)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Python-009688?style=for-the-badge&logo=fastapi)](https://ai-dungeon-master-api.onrender.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

---

## 🎮 Demo

**Live App:** [ai-dungeon-master-coral.vercel.app](https://ai-dungeon-master-coral.vercel.app)

> **Note:** The live demo runs on free-tier cloud infrastructure. For the **best experience with instant responses**, run it locally (setup takes under 2 minutes — see below).

---

## ✨ Features

- 🤖 **Multi-Agent AI Pipeline** — Narrator agent streams the story in real-time; a silent Extractor agent parses structured game events (items, quests, gold, XP) from each response
- 🧠 **Semantic RAG Memory** — ChromaDB + Sentence Transformers (`all-MiniLM-L6-v2`) gives the DM long-term contextual memory across sessions
- ⚡ **Real-time Streaming** — Token-by-token story delivery over WebSockets — the DM types the story as it thinks
- 📜 **Persistent Game State** — Full PostgreSQL-backed persistence (Neon): character sheets, inventory, quest log, NPC memory, and full turn history
- 🔐 **Auth System** — Username/password registration with bcrypt hashing
- 🗺️ **Multi-Campaign** — Create and switch between multiple independent adventures
- 🌐 **Full-Stack** — Next.js 15 (App Router) frontend + FastAPI backend, deployed independently

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                     |
│  AuthPage → CampaignSelect → ChatPanel + Sidebar        │
│  (Vercel)           WebSocket (wss://)                  │
└──────────────────────┬──────────────────────────────────┘
                       │ wss://
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend                       |
│                                                         │
│   WebSocket Handler                                     │
│        │                                                │
│   ┌────▼─────────────────────────┐                      │
│   │     GameAgentWorkflow        │                      │
│   │  ┌──────────┐  ┌──────────┐  │                      │
│   │  │ Narrator │→ │Extractor │  │  ← Two-agent pipeline│
│   │  │  (LLM)   │  │  (LLM)   │  │                      │
│   │  └──────────┘  └──────────┘  │                      │
│   └──────────────────────────────┘                      │
│        │                                                │
│   ┌────▼──────────────────────────────┐                 │
│   │         Memory Stack              │                 │
│   │  WorkingMemory (last 5 turns)     │                 │
│   │  ChromaDB (semantic vector store) │                 │
│   │  PostgreSQL (full persistence)    │                 │
│   └───────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────┘
                       │
        ┌──────────────┴─────────────┐
        │                            │
   ┌────▼─────┐              ┌───────▼──────┐
   │  Groq    │              │     Neon     │
   │ LLaMA-3  │              │  PostgreSQL  │
   │  (70B)   │              │   (Cloud)    │
   └──────────┘              └──────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | Groq API · LLaMA 3.3 70B Versatile |
| **Backend** | Python 3.11 · FastAPI · Uvicorn |
| **WebSockets** | Native FastAPI WebSocket |
| **Database** | PostgreSQL (Neon) · SQLAlchemy 2.0 |
| **Vector Memory** | ChromaDB · Sentence Transformers |
| **Frontend** | Next.js 15 · TypeScript · App Router |
| **Auth** | bcrypt · localStorage session |
| **Deployment** | Render (backend) · Vercel (frontend) · Docker |

---

## 🚀 Local Setup (Recommended)

### Prerequisites
- Python 3.11+
- Node.js 18+
- A [Groq API Key](https://console.groq.com) (free)

### 1. Clone & Configure

```bash
git clone https://github.com/utsavukani/ai-dungeon-master.git
cd ai-dungeon-master
```

Create `.env` in the root:
```env
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=sqlite:///./data/game.db
```

> **SQLite is used locally** — no database setup needed. For cloud PostgreSQL, use a [Neon](https://neon.tech) connection string.

### 2. Backend

```bash
pip install -r requirements.txt
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend runs at `http://localhost:8000`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`

### 4. Play

1. Open `http://localhost:3000`
2. Register an account
3. Create a campaign
4. Start your adventure ⚔️

---

## 🌐 Cloud Deployment

The project is production-ready and deployed using:

| Service | Role | URL |
|---------|------|-----|
| **Vercel** | Frontend hosting | [ai-dungeon-master-coral.vercel.app](https://ai-dungeon-master-coral.vercel.app) |
| **Render** | Backend + Docker | [ai-dungeon-master-api.onrender.com](https://ai-dungeon-master-api.onrender.com) |
| **Neon** | Cloud PostgreSQL | Managed |

### Environment Variables

**Backend (Render):**
```
DATABASE_URL=postgresql://...@...neon.tech/neondb?sslmode=require
GROQ_API_KEY=your_key
```

**Frontend (Vercel):**
```
NEXT_PUBLIC_API_URL=https://ai-dungeon-master-api.onrender.com
```

---

## 📁 Project Structure

```
ai-dungeon-master/
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI app + CORS
│   │   ├── routes.py        # REST endpoints (auth, campaigns, character, quests)
│   │   └── websockets.py    # WebSocket game handler
│   ├── game/
│   │   ├── game_engine.py   # Core game loop orchestrator
│   │   ├── agent_graph.py   # Multi-agent workflow (Narrator → Extractor)
│   │   ├── character_sheet.py
│   │   └── quest_tracker.py
│   ├── memory/
│   │   └── memory_manager.py  # Working + Vector + SQL memory stack
│   ├── llm/
│   │   └── provider.py        # Groq API client (streaming + JSON mode)
│   └── database/
│       ├── database.py        # SQLAlchemy engine + init
│       └── models.py          # ORM models (User, Campaign, Character, Quest, NPC...)
├── frontend/
│   └── src/
│       ├── app/               # Next.js App Router
│       ├── components/        # AuthPage, CampaignSelect, ChatPanel, Sidebar
│       └── lib/api.ts         # Centralized API URL config
├── Dockerfile                 # Production Docker image
└── requirements.txt
```

---

## 🎯 Key Engineering Decisions

- **Custom Agent Orchestrator** — Replaced LangGraph's `StateGraph` with a lightweight sequential `async` workflow. Eliminated a heavy dependency while preserving the multi-agent architecture concept, reducing Docker image overhead.

- **Hybrid Memory Architecture** — Three-tier memory: Working Memory (last N turns in RAM), ChromaDB (semantic similarity search across all turns), and PostgreSQL (full structured persistence). Gives the DM genuinely contextual recall.

- **Database Abstraction** — `database.py` auto-detects SQLite (local) vs PostgreSQL (cloud) and applies appropriate connection settings including SSL, enabling zero-config local development with production-grade cloud deployment.

- **WebSocket Streaming** — The Narrator agent streams each token directly to the frontend via WebSocket callbacks, giving the DM its characteristic "typing" effect.

---

## 📄 License

MIT — feel free to use this as a reference for your own AI/full-stack projects.

---

*Built as a portfolio project demonstrating AI engineering, full-stack development, and cloud deployment skills.*
