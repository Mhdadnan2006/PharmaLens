# Running PharmaLens locally

This file describes how to run the backend and frontend locally, and common troubleshooting steps (OneDrive, SWC). Follow these commands on Windows PowerShell.

## Backend (FastAPI)

1. Create a Python virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

2. Start the backend server (development):

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000
```

- Backend will be available at `http://localhost:8000`.
- Required environment variables for optional features (LLM report generation):
  - `GROQ_API_KEY` — if you integrate Groq.
  - `GEMINI_API_KEY` — for Gemini fallback.

## Frontend (Next.js)

1. From the `frontend` folder install packages and start dev server:

```powershell
cd frontend
npm install
npm run dev
```

- Next will start on port 3000 by default; if 3000 is in use it will fall back to the next available port (e.g. 3001). The terminal prints the local URL.
- If you see warnings about patched `@next/swc` after running `next dev`, run `npm install` to download the binaries.

## OneDrive notes and Windows permission issues

If you experience `EPERM` or locked-file errors when installing `node_modules` (commonly on `@next/swc-win32-x64-msvc`), this is often caused by OneDrive syncing or antivirus locking binary files.

Recommended options:

- Preferred: move the repo outside OneDrive to a local folder such as `C:\Projects\PharmaLensApi` and run `npm install` again.
- Alternative: pause OneDrive sync temporarily (via the OneDrive tray icon), then remove `node_modules` and `package-lock.json`, clear the npm cache and reinstall:

```powershell
# from frontend
rd /s /q node_modules
del package-lock.json
npm cache clean --force
npm install
```

- If a single file is locked, you can attempt to take ownership and delete it (try the preferred options first):

```powershell
# run as Administrator
takeown /f .\node_modules\@next\swc-win32-x64-msvc\next-swc.win32-x64-msvc.node
icacls .\node_modules\@next\swc-win32-x64-msvc\next-swc.win32-x64-msvc.node /grant %USERNAME%:F
del .\node_modules\@next\swc-win32-x64-msvc\next-swc.win32-x64-msvc.node
rd /s /q node_modules
npm install
```

## Quick verification

- Health endpoint:

```powershell
curl http://localhost:8000/health
```

- Test prediction (replace `aspirin` with any drug):

```powershell
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"drug_name":"aspirin"}'
```

- Open the frontend in your browser: `http://localhost:3000` (or the port printed by Next).

## Report download

- On the `Predict` page, run a prediction and click `Download PDF Report`. The backend `POST /report` endpoint returns a PDF generated server-side.

## Troubleshooting

- If Next warns "Lockfile was successfully patched, please run \"npm install\"", run `npm install`.
- If backend errors with `ModuleNotFoundError: reportlab`, ensure `reportlab` is installed in your venv (`pip install reportlab` or `pip install -r requirements.txt`).
- If ports conflict, stop other local servers or use the `--port` flag for `uvicorn` / set `PORT` environment variable for Next.

## Notes for deployment

- Dockerfile exists for backend; CI/Actions workflows are included in the repo for deploying to Hugging Face Spaces.
- Ensure LLM keys are set in CI secrets for report generation.

If you want, I can create a short `docker-compose.yml` to run both services locally in containers; say so and I'll add it.
