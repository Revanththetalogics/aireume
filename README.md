# AI Resume Screener by ThetaLogics

A local-first AI-powered SaaS for recruiters to analyze resumes against job descriptions using Ollama (llama3). Built with FastAPI backend, React frontend, and deployed via Docker to a VPS with Portainer.

**Live URL:** https://airesume-staging.thetalogics.com

---

## Features

- Upload resumes (PDF/DOCX)
- Paste job descriptions
- AI-powered analysis returning:
  - Fit score (0-100)
  - Strengths and weaknesses
  - Employment gap detection
  - Education analysis
  - Risk signals (fake patterns, job hopping, etc.)
  - Final recommendation (Shortlist | Consider | Reject)

---

## Tech Stack

**Backend:**
- Python 3.11
- FastAPI
- SQLAlchemy (SQLite)
- pdfplumber (PDF parsing)
- python-docx (DOCX parsing)
- httpx (Ollama API)

**Frontend:**
- React 18
- Vite
- TailwindCSS
- react-dropzone
- axios
- lucide-react

**Infrastructure:**
- Docker & Docker Compose
- Nginx (reverse proxy + SSL)
- Ollama (local LLM)
- Certbot (Let's Encrypt SSL)

**CI/CD:**
- GitHub Actions
- Docker Hub
- VPS deployment via SSH

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- Ollama (install from https://ollama.com)

### Step 1: Start Ollama
```bash
ollama pull llama3
ollama serve
```

### Step 2: Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend
cd app/backend
uvicorn main:app --reload --port 8000
```

### Step 3: Frontend Setup
```bash
cd app/frontend
npm install
npm run dev
```

### Step 4: Open Browser
Frontend: http://localhost:5173  
Backend API: http://localhost:8000  
API Docs: http://localhost:8000/docs

---

## Local Development with Docker

If you prefer using Docker locally:

```bash
# Build and start all services
docker-compose up --build

# In another terminal, pull the model
docker exec -it resume-screener-ollama-1 ollama pull llama3
```

Access the app at http://localhost:80

---

## Production Deployment (VPS)

### Step 1: Initial VPS Setup

SSH into your VPS and run these commands:

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh

# 2. Add user to docker group (logout and login after this)
sudo usermod -aG docker $USER

# 3. Create app directory
sudo mkdir -p /opt/resume-screener
sudo chown $USER:$USER /opt/resume-screener

# 4. Install Certbot
sudo apt update
sudo apt install -y certbot

# 5. Obtain SSL certificate
sudo certbot certonly --standalone \
  -d airesume-staging.thetalogics.com \
  --email your@email.com \
  --agree-tos \
  --non-interactive
```

### Step 2: Add DNS Record

In your domain provider, add an A record:
- Name: `airesume-staging`
- Value: `66.70.191.79`
- TTL: 300

### Step 3: Configure GitHub Secrets

Go to GitHub → Settings → Secrets and variables → Actions → New repository secret

Add these 5 secrets:

| Secret Name | Value |
|-------------|-------|
| `DOCKERHUB_USERNAME` | `revanth2245` |
| `DOCKERHUB_TOKEN` | Your Docker Hub access token |
| `VPS_HOST` | `66.70.191.79` |
| `VPS_USERNAME` | `ubuntu` |
| `VPS_SSH_KEY` | Your SSH private key (full content including begin/end lines) |

### How to generate SSH key:

On your Windows PC, run in PowerShell:
```powershell
# Create .ssh folder if needed
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.ssh"

# Generate key (press Enter for passphrase - leave empty)
ssh-keygen -t ed25519 -C "github-actions" -f "$env:USERPROFILE\.ssh\github_actions_vps"

# Add public key to VPS (run this in PowerShell)
Get-Content "$env:USERPROFILE\.ssh\github_actions_vps.pub" | ssh ubuntu@66.70.191.79 "cat >> ~/.ssh/authorized_keys"

# Copy private key for GitHub secret
Get-Content "$env:USERPROFILE\.ssh\github_actions_vps"
```

Copy the entire output (including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`) and paste into GitHub as `VPS_SSH_KEY`.

### Step 4: First Deploy

After setting up secrets, push your code to the `main` branch. GitHub Actions will automatically:
1. Run tests
2. Build Docker images
3. Push to Docker Hub
4. SSH to your VPS
5. Deploy the stack

### Step 5: Pull the AI Model (one-time)

After first deploy, pull llama3:
```bash
ssh ubuntu@66.70.191.79
docker exec -it resume-screener-ollama ollama pull llama3
```

This downloads ~4GB and takes 5-10 minutes.

---

## API Endpoints

### POST /api/analyze
Upload resume and job description for analysis.

**Request:**
- `resume` (file): PDF or DOCX file
- `job_description` (string): Job description text

**Response:**
```json
{
  "fit_score": 75,
  "strengths": ["Strong Python skills", "5+ years experience"],
  "weaknesses": ["Limited cloud experience"],
  "employment_gaps": [],
  "education_analysis": "Relevant CS degree from good university",
  "risk_signals": [],
  "final_recommendation": "Shortlist"
}
```

### GET /api/history
Get list of previous screenings.

### GET /health
Health check endpoint.

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│    Nginx    │────▶│   React     │
│             │     │   (443/SSL) │     │  Frontend   │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   FastAPI   │
                                        │   Backend   │
                                        └─────────────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          ▼                    ▼                    ▼
                   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
                   │   Ollama    │      │   SQLite    │      │  File       │
                   │   (llama3)  │      │   Database  │      │  Uploads    │
                   └─────────────┘      └─────────────┘      └─────────────┘
```

---

## Testing

### Backend Tests
```bash
pytest app/backend/tests/ -v
```

### Frontend Tests
```bash
cd app/frontend
npm test
```

### GitHub Actions
Tests run automatically on every Pull Request to `main` or `staging` branches.

---

## Project Structure

```
.
├── app/
│   ├── backend/
│   │   ├── db/
│   │   │   └── database.py
│   │   ├── models/
│   │   │   ├── db_models.py
│   │   │   └── schemas.py
│   │   ├── routes/
│   │   │   └── analyze.py
│   │   ├── services/
│   │   │   ├── parser_service.py
│   │   │   ├── gap_detector.py
│   │   │   ├── analysis_service.py
│   │   │   └── llm_service.py
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── test_parser_service.py
│   │   │   ├── test_gap_detector.py
│   │   │   ├── test_analysis_service.py
│   │   │   └── test_api.py
│   │   ├── main.py
│   │   └── Dockerfile
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── UploadForm.jsx
│   │   │   │   ├── ScoreGauge.jsx
│   │   │   │   ├── ResultCard.jsx
│   │   │   │   └── Timeline.jsx
│   │   │   ├── pages/
│   │   │   │   └── Dashboard.jsx
│   │   │   ├── lib/
│   │   │   │   └── api.js
│   │   │   ├── __tests__/
│   │   │   │   ├── setup.js
│   │   │   │   ├── ScoreGauge.test.jsx
│   │   │   │   ├── ResultCard.test.jsx
│   │   │   │   └── UploadForm.test.jsx
│   │   │   ├── main.jsx
│   │   │   ├── App.jsx
│   │   │   └── index.css
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── vite.config.js
│   │   ├── tailwind.config.js
│   │   └── Dockerfile
│   └── nginx/
│       ├── nginx.conf        # Local dev
│       └── nginx.prod.conf   # Production
├── .github/workflows/
│   ├── ci.yml
│   └── cd.yml
├── docker-compose.yml        # Local dev
├── docker-compose.prod.yml   # Production
├── requirements.txt
└── README.md
```

---

## Troubleshooting

### Ollama not responding
```bash
docker logs resume-screener-ollama
# Pull the model if needed
docker exec resume-screener-ollama ollama pull llama3
```

### Database locked errors
SQLite doesn't support concurrent writes. If you see "database is locked", restart the backend container.

### SSL certificate issues
```bash
# Renew certificate manually on VPS
sudo certbot renew
# Restart nginx
docker compose -f /opt/resume-screener/docker-compose.prod.yml restart nginx
```

### Deploy not working
Check GitHub Actions logs for errors. Common issues:
- Docker Hub token expired
- SSH key not added to VPS authorized_keys
- VPS firewall blocking SSH

---

## License

MIT License - Copyright (c) 2024 ThetaLogics

---

## Support

For issues or questions, please open a GitHub issue.
# Trigger deploy
