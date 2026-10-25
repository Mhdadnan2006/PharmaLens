---
sdk: docker
app_port: 7860
---

# PharmaLens

PharmaLens is a two-part project:

- Backend: FastAPI service that exposes `/predict`, `/metrics`, and `/latency`.
- Frontend: Next.js React app that consumes the backend and renders predictions and dashboards.

Architecture
- Backend Docker image serves the FastAPI app on port `7860`.
- Frontend is a Next.js app deployed on Vercel and configured to call the backend via `NEXT_PUBLIC_API_URL`.

Local development

1. Backend

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 7860
```

2. Frontend

```bash
cd frontend
npm install
# Point NEXT_PUBLIC_API_URL to http://localhost:8000 by default or your deployed backend
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Deployment

- Backend: Deploy to Hugging Face Spaces using the Docker SDK. The repo includes a `Dockerfile` and this `README.md` metadata header so Spaces will run the container on port `7860`.
- Frontend: Deploy to Vercel. Set `NEXT_PUBLIC_API_URL` to the deployed backend URL.

CI / CD

- A GitHub Actions workflow (`.github/workflows/deploy-backend.yml`) is included to lint/build the project and push the backend files (Dockerfile, requirements, README) to the HF Space repo on merge to `main`.

Required secrets for backend deploy (set in GitHub repository settings):

- `HF_USERNAME` — your Hugging Face username
- `HF_TOKEN` — your Hugging Face API token with repo access
- `HF_SPACE_REPO` — the Hugging Face Space repository in the form `username/space-name`

LLM integration environment variables (set on the deployed backend host):

- `GROQ_API_KEY` — API key for Groq LLM (primary)
- `GEMINI_API_KEY` — API key for Google Gemini (fallback)

When live, update this README with links to the deployed services:

- Backend (HF Space): https://<your-space>.hf.space
- Frontend (Vercel): https://<your-vercel-domain>
