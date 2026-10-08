# 🚀 Memory Lane RAG — Deployment Guide

This guide covers four proven production deployment pathways for **Memory Lane RAG**, ranging from zero-config cloud PaaS to self-hosted VPS setups.

---

## 📋 Overview of Architecture & Storage Needs

Memory Lane RAG consists of:
1. **FastAPI Backend (Python 3.10+)**: Runs Uvicorn on port `8000`.
2. **React 18 Frontend (TypeScript + Vite)**: Single Page App. In production, it can be served directly by FastAPI or hosted separately on Vercel/Netlify.
3. **Persistent Storage (`data/storage/`)**:
   - `memory_lane.db` (SQLite relational DB & FTS5 full-text index)
   - `vectors/` (Cosine similarity vectors)
   - `uploads/` (Uploaded raw documents)

> **Important**: Ensure your hosting provider supports persistent disk storage for `data/storage` so data persists across restarts.

---

## ⚡ Option 1: Render.com (Recommended Cloud Deployment)

Render allows you to deploy either as a **Unified Docker Web Service** (easiest) or as **Two Services** (Backend Web Service + Frontend Static Site).

### Method A: Unified Docker Web Service (Single URL, Zero CORS)

1. Log into [Render Dashboard](https://dashboard.render.com/) and click **New +** $\rightarrow$ **Web Service**.
2. Connect your GitHub repository: `https://github.com/ShakilUrRehman21/memory-lane-rag`.
3. Select **Docker** environment (Render automatically detects the root `Dockerfile`).
4. Set the following configurations:
   - **Name**: `memory-lane-rag`
   - **Region**: Choose the closest region (e.g., Frankfurt, Oregon)
   - **Branch**: `main`
   - **Instance Type**: `Starter` ($7/mo) or Free tier
5. Add **Environment Variables** (Optional):
   - `GEMINI_API_KEY`: *(Your Google AI Studio key, optional)*
   - `OPENAI_API_KEY`: *(Your OpenAI API key, optional)*
6. Add **Disk Storage** (under the Disks tab):
   - **Mount Path**: `/app/data/storage`
   - **Size**: `1 GB` (or more as needed)
7. Click **Create Web Service**. Render will build the React frontend, set up Python, seed the database, and serve both on a single `.onrender.com` URL!

---

## 🚂 Option 2: Railway.app (One-Click Docker)

1. Go to [Railway.app](https://railway.app/) and create a new project.
2. Select **Deploy from GitHub repo** and pick `memory-lane-rag`.
3. Railway automatically detects `Dockerfile`.
4. Go to **Settings** $\rightarrow$ **Volumes** $\rightarrow$ **Add Volume**:
   - Set **Mount Path** to `/app/data/storage`.
5. Under **Variables**, add any optional LLM keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`).
6. Under **Networking**, click **Generate Domain**.
7. Railway will deploy the application and expose your public URL.

---

## 🐳 Option 3: Docker & Docker Compose (Self-Hosted VPS)

Ideal for DigitalOcean Droplets, Hetzner Cloud, AWS EC2, or Linode.

### 1. Connect to your VPS and install Docker
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
```

### 2. Clone the Repository
```bash
git clone https://github.com/ShakilUrRehman21/memory-lane-rag.git
cd memory-lane-rag
```

### 3. Configure Environment Variables (Optional)
```bash
cp .env.example .env
# Edit keys if desired
nano .env
```

### 4. Start the Application
```bash
docker compose up -d --build
```

The container starts with:
- React frontend built and served
- FastAPI backend running on port `8000`
- Persistent named volume `memory_lane_data` backing `/app/data/storage`
- Pre-seeded multi-year personas (`alex_chen`, `sophia_taylor`, `marcus_vance`)

### 5. Check Logs and Health
```bash
# View live logs
docker compose logs -f

# Check health endpoint
curl http://localhost:8000/api/health
```

---

## 🌐 Option 4: Split Deployment (Vercel Frontend + Render/Railway Backend)

If you prefer hosting the React client on Vercel's global CDN:

### 1. Deploy the Backend (Render or Railway)
- Deploy `backend/` following Option 1 or 2.
- Note your live backend URL (e.g., `https://memory-lane-api.onrender.com`).

### 2. Deploy Frontend to Vercel
1. Go to [Vercel](https://vercel.com/) and click **Add New Project**.
2. Select the `memory-lane-rag` repository.
3. Configure the project:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. In **Environment Variables**, add:
   ```env
   VITE_API_BASE_URL=https://memory-lane-api.onrender.com
   ```
5. Click **Deploy**. Vercel will build and route all API calls to your live backend.

---

## 🖥️ Option 5: Traditional Ubuntu Linux VPS (Nginx + Systemd)

### 1. Install System Packages
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip nodejs npm nginx certbot python3-certbot-nginx
```

### 2. Setup App Directory
```bash
git clone https://github.com/ShakilUrRehman21/memory-lane-rag.git /opt/memory-lane-rag
cd /opt/memory-lane-rag

# Backend Virtual Environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python backend/app/seed.py

# Frontend Build
cd frontend
npm install
npm run build
cd ..
```

### 3. Create Systemd Service (`/etc/systemd/system/memory-lane.service`)
```ini
[Unit]
Description=Memory Lane RAG FastAPI Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/memory-lane-rag
ExecStart=/opt/memory-lane-rag/.venv/bin/python backend/run.py
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo chown -R www-data:www-data /opt/memory-lane-rag
sudo systemctl daemon-reload
sudo systemctl enable --now memory-lane.service
```

### 4. Configure Nginx Reverse Proxy (`/etc/nginx/sites-available/memory-lane`)
```nginx
server {
    server_name yourdomain.com;

    # Serve built React frontend
    location / {
        root /opt/memory-lane-rag/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site and acquire SSL:
```bash
sudo ln -s /etc/nginx/sites-available/memory-lane /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d yourdomain.com
```

---

## 🔍 Post-Deployment Verification Checklist

Once deployed, verify your instance:

| Check | Target | Expected Result |
| :--- | :--- | :--- |
| **Health API** | `GET /api/health` | `{"status": "healthy", "service": "Memory Lane RAG"}` |
| **Pre-seeded Users** | `GET /api/users` | List of 3 personas (`alex_chen`, `sophia_taylor`, `marcus_vance`) |
| **Web UI** | Open your URL in browser | Interactive dashboard loads with dark-mode aesthetic |
| **Ask Query** | Ask a longitudinal query | Returns streaming response with verified citation claims |
| **Research Studio** | Run benchmark test | Executes 3-way RAG comparison in $< 1\text{s}$ |
