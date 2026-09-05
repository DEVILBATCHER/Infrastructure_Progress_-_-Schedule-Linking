SIH26122 — Intelligent Data Capture & Schedule-Linking Layer

An AI-powered system that automatically links free-text daily progress reports to their correct schedule activities in infrastructure project management — built for Smart India Hackathon 2026.

Problem

On infrastructure projects, daily progress is logged as free text by field teams (e.g. "12 inch spool erection completed at Unit 3"), while the master schedule tracks work as structured Activity IDs (e.g. "P101 — Install 12-inch carbon steel pipeline"). Matching the two manually is slow and error-prone. This project automates that link using NLP-based semantic matching, with a human-in-the-loop approval step.

How it works
Daily Report → Text Extraction → Normalization → Embeddings → Candidate Retrieval
→ Similarity / Reranking → Confidence Scoring → Top Matches → Human Approval
A daily report (free text) is uploaded.
The text is extracted, cleaned, and normalized.
It's converted into a vector embedding.
The system retrieves the closest candidate Activity IDs from the schedule.
Candidates are reranked by similarity and assigned a confidence score.
The top matches are shown to the user for final approval or correction.
Team & roles
Role	Owns	Stack
AI/NLP	Matching engine (text extraction → confidence scoring)	Python, Sentence Transformers, vector search
Backend + Database	API layer connecting everything	FastAPI, PostgreSQL
Frontend — Dashboard	Analytics & metrics dashboard	React
Frontend — Workflow/UI	Upload → review → approve/reject screens	React

The backend is the shared contract everyone depends on — see API Contract below.

Tech stack
AI/NLP: Python, Sentence Transformers, vector similarity search
Backend: FastAPI, PostgreSQL
Frontend: React
Project structure
├── ai-engine/          # matching engine: preprocessing, embeddings, retrieval, scoring
├── backend/            # FastAPI app, PostgreSQL models, API routes
├── frontend-dashboard/ # analytics dashboard (React)
├── frontend-workflow/  # upload/review/approve UI (React)
├── API_CONTRACT.md     # shared source of truth for endpoint shapes
└── README.md
API contract

Key endpoints exposed by the backend (see API_CONTRACT.md for exact request/response shapes — update it whenever an endpoint changes):

POST /upload-report — submit a daily report for matching
POST /match — trigger matching against the schedule
GET /matches — fetch matching results
GET /activities — fetch schedule activities
POST /approve-match — approve or reject a suggested match
Getting started
bash
# clone the repo
git clone <repo-url>
cd sih26122

# backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# frontend (dashboard or workflow)
cd frontend-dashboard   # or frontend-workflow
npm install
npm start
Branching workflow
main — always stable/demo-ready
One feature branch per person/feature, merged via pull request
Coordinate API contract changes in API_CONTRACT.md before building against them
Status

🚧 In active development for Smart India Hackathon 2026.
