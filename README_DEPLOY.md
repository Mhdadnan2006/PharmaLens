# Deployment checklist

1. Backend (Hugging Face Spaces)
   - Ensure `HF_TOKEN`, `HF_USERNAME`, and `HF_SPACE_REPO` secrets are set in GitHub.
   - On merge to `main`, the workflow will build the Docker image and push files to the HF Space repo.

2. Frontend (Vercel)
   - Configure `NEXT_PUBLIC_API_URL` environment variable in Vercel to point at the HF Space URL.
