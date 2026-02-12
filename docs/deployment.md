# 🚀 Production Deployment Guide

> **Stack**: Vercel (Frontend) + Railway (Backend) + Supabase (PostgreSQL Database)
>
> Estimated time: ~20 minutes

---

## 📋 Prerequisites

| Service | URL | What you need |
|---------|-----|---------------|
| GitHub | [github.com](https://github.com) | Push this repo to a GitHub repository |
| Supabase | [supabase.com](https://supabase.com) | Free tier — PostgreSQL database |
| Railway | [railway.app](https://railway.app) | Starter plan — Python backend hosting |
| Vercel | [vercel.com](https://vercel.com) | Free tier — Frontend hosting |

---

## Architecture Overview

```
┌─────────────────┐     HTTPS      ┌──────────────────┐     PostgreSQL     ┌─────────────────┐
│   Vercel         │ ─────────────→ │   Railway          │ ──────────────→ │   Supabase        │
│   (Vite Frontend)│  /api/* proxy  │   (FastAPI Backend) │  DATABASE_URL   │   (PostgreSQL DB) │
│   vercel.json    │                │   railway.json      │                 │   Connection Pool │
└─────────────────┘                └──────────────────┘                    └─────────────────┘
```

---

## Step 1: Database Setup (Supabase) 🗄️

### 1.1 — Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) → **New Project**
2. Enter:
   - **Project Name**: `smart-campus-store`
   - **Database Password**: Choose a strong password (save it!)
   - **Region**: Select the one closest to your users
3. Click **Create new project** → wait ~2 minutes

### 1.2 — Get the Connection String

1. Go to **Project Settings** (⚙️ icon) → **Database**
2. Scroll to **Connection string** → select **URI** tab
3. Select **Mode: Transaction** (recommended for serverless-like workloads)
4. Copy the connection string. It looks like:
   ```
   postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
5. ⚠️ Replace `[YOUR-PASSWORD]` with your actual database password
6. ⚠️ If your password contains special characters (`@`, `#`, `%`, etc.), URL-encode them

### 1.3 — (Optional) Run Schema Manually

> **Note**: SQLAlchemy's `create_all()` auto-creates tables on first backend startup.
> You only need manual SQL if you want indexes & triggers for better performance.

1. Go to **SQL Editor** in Supabase
2. Click **New Query**
3. Paste the contents of [`docs/supabase_schema.sql`](./supabase_schema.sql)
4. Click **Run**

---

## Step 2: Backend Deployment (Railway) 🚂

### 2.1 — Create a Railway Project

1. Go to [railway.app](https://railway.app) → **New Project**
2. Select **Deploy from GitHub repo**
3. Connect your GitHub account and select this repository
4. Railway will auto-detect the Python project

### 2.2 — Configure Railway Settings

Railway will read the `railway.json` file automatically. Verify these settings:

| Setting | Value |
|---------|-------|
| **Builder** | Nixpacks (auto-detected from `nixpacks.toml`) |
| **Root Directory** | `/` (project root) |
| **Start Command** | Auto-read from `railway.json` |

### 2.3 — Set Environment Variables

Go to your Railway service → **Variables** tab → **Add Variable**:

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | `postgresql://postgres.[ref]:[pw]@aws-0-[region].pooler.supabase.com:6543/postgres` | From Supabase Step 1.2 |
| `CORS_ORIGINS` | `*` | ⚠️ Set to `*` initially, update after Vercel deploy |
| `PORT` | _(leave empty)_ | Railway sets this automatically |

### 2.4 — Deploy

1. Click **Deploy** (or push to `main` — auto-deploys)
2. Wait for build to complete (~3-5 minutes on first deploy)
3. Once **Active**, go to **Settings** → **Networking** → **Generate Domain**
4. Copy your Railway URL, e.g.:
   ```
   https://smart-campus-store-production.up.railway.app
   ```

### 2.5 — Verify Backend

Open in browser:
```
https://YOUR-RAILWAY-URL.up.railway.app/docs
```
You should see the FastAPI Swagger documentation page.

---

## Step 3: Frontend Deployment (Vercel) ▲

### 3.1 — Create a Vercel Project

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project**
2. **Import Git Repository** → Select this repository
3. Configure:

| Setting | Value |
|---------|-------|
| **Framework Preset** | `Vite` |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` (auto-detected) |
| **Output Directory** | `dist` (auto-detected from vite.config.js, outputs to `../dist` relative to frontend, which is `dist` relative to root) |

### 3.2 — Set Environment Variables

In the Vercel project settings → **Environment Variables**:

| Variable | Value | Environment |
|----------|-------|-------------|
| `VITE_API_URL` | `https://YOUR-RAILWAY-URL.up.railway.app` | Production |

> ⚠️ **IMPORTANT**: Do NOT add a trailing slash `/` to the URL
>
> ⚠️ **IMPORTANT**: Vite env vars must start with `VITE_` to be exposed to the frontend

### 3.3 — Deploy

1. Click **Deploy**
2. Wait for build (~1-2 minutes)
3. Copy your Vercel URL, e.g.:
   ```
   https://smart-campus-store.vercel.app
   ```

### 3.4 — (Alternative) API Proxy via vercel.json

The `frontend/vercel.json` includes a `rewrites` rule that proxies `/api/*` requests to your Railway backend. To use this:

1. Edit `frontend/vercel.json`
2. Replace `YOUR_RAILWAY_BACKEND_URL` with your actual Railway domain:
   ```json
   {
     "source": "/api/:path*",
     "destination": "https://smart-campus-store-production.up.railway.app/api/:path*"
   }
   ```
3. If using the proxy, you can leave `VITE_API_URL` empty (requests will go through Vercel's edge)

---

## Step 4: Connect Frontend ↔ Backend (CORS) 🔗

### 4.1 — Update Railway CORS

Now that you have the Vercel URL, go back to Railway:

1. **Variables** tab → Edit `CORS_ORIGINS`
2. Set it to your exact Vercel URL (no trailing slash):
   ```
   https://smart-campus-store.vercel.app
   ```
3. For multiple origins (e.g., custom domain + Vercel):
   ```
   https://smart-campus-store.vercel.app,https://store.yourcampus.edu
   ```

### 4.2 — Redeploy Railway

Railway will auto-redeploy when variables change. If not, click **Redeploy**.

---

## Step 5: Verification Checklist ✅

Open your Vercel URL and verify each item:

| # | Check | How to verify |
|---|-------|---------------|
| 1 | 🏠 Dashboard loads | Open the homepage — KPI cards should show data |
| 2 | 📦 Products list | Navigate to Inventory → products should appear |
| 3 | 🔔 Expiry alerts | Check Expiry Monitor → batches with expiry dates should show |
| 4 | 💰 Sales work | Try recording a sale transaction |
| 5 | 📊 Analytics load | Charts and revenue graphs should render |
| 6 | 🤖 ML predictions | Seasonal predictions tab should show data |
| 7 | 🌐 Network tab | Open DevTools (F12) → Network → all `/api/*` calls go to Railway (not localhost) |
| 8 | 🔒 No CORS errors | Console should be free of CORS errors |

---

## 🔧 Exact Settings Summary

### Vercel Settings
```
Framework Preset:  Vite
Root Directory:    frontend
Build Command:     npm run build
Output Directory:  dist
Environment Vars:  VITE_API_URL = https://YOUR-RAILWAY-URL.up.railway.app
```

### Railway Settings
```
Builder:           Nixpacks (reads nixpacks.toml)
Start Command:     . /opt/venv/bin/activate && gunicorn backend.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 2 --timeout 120
Health Check:      /api/dashboard/kpi
Environment Vars:
  DATABASE_URL   = postgresql://postgres.[ref]:[pw]@aws-0-[region].pooler.supabase.com:6543/postgres
  CORS_ORIGINS   = https://your-vercel-app.vercel.app
```

### Supabase Settings
```
DB Type:           PostgreSQL (auto-managed)
Connection Mode:   Transaction (port 6543)
Tables:            Auto-created by SQLAlchemy on first startup
Optional SQL:      docs/supabase_schema.sql (for indexes + triggers)
```

---

## 🚑 Troubleshooting

### Database Errors
| Symptom | Cause | Fix |
|---------|-------|-----|
| `OperationalError: could not connect` | Wrong DATABASE_URL | Double-check Supabase connection string, password, region |
| `password authentication failed` | Special chars in password | URL-encode special characters (`@` → `%40`, `#` → `%23`) |
| `relation does not exist` | Tables not created | Backend auto-creates on startup — check Railway logs for errors |

### CORS Errors
| Symptom | Cause | Fix |
|---------|-------|-----|
| `Access-Control-Allow-Origin` error | CORS_ORIGINS mismatch | Ensure Railway's `CORS_ORIGINS` exactly matches Vercel URL |
| CORS error with trailing slash | URL format | Remove trailing `/` from both `CORS_ORIGINS` and `VITE_API_URL` |

### Frontend Issues
| Symptom | Cause | Fix |
|---------|-------|-----|
| Blank page | Missing VITE_API_URL | Set `VITE_API_URL` in Vercel env vars → Redeploy |
| API calls to localhost | VITE_API_URL not set at build time | Must be set *before* build — redeploy after adding |
| 404 on page refresh | SPA routing | The `vercel.json` rewrites handle this |

### Railway Build Failures
| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: scikit-learn` | Build cache stale | Clear Railway build cache → Redeploy |
| `gcc: fatal error` | Missing build deps | `nixpacks.toml` includes gcc, openblas — check it exists in root |
| Timeout on startup | ML training slow | CSV training happens on startup; first deploy may take longer |

---

## 🔄 CI/CD Pipeline

Pushing to `main` triggers automatic deployments:

| Service | Trigger | What happens |
|---------|---------|--------------|
| **Vercel** | Push to `main` | Auto-builds frontend, deploys to CDN |
| **Railway** | Push to `main` | Auto-builds backend, runs health check, swaps deployment |
| **Supabase** | Backend startup | SQLAlchemy `create_all()` syncs schema |
| **GitHub Actions** | Push/PR to `main` | Runs linting + backend tests + Playwright E2E tests |

---

## 📁 Config Files Reference

| File | Purpose | Used by |
|------|---------|---------|
| `frontend/vercel.json` | Vercel build + rewrite config | Vercel |
| `railway.json` | Railway deploy config | Railway |
| `nixpacks.toml` | Nixpacks build instructions (Python deps, venv) | Railway (via Nixpacks) |
| `Procfile` | Gunicorn start command (fallback) | Railway / Heroku |
| `requirements.txt` | Python dependencies | Railway / pip |
| `frontend/package.json` | Frontend dependencies + scripts | Vercel / npm |
| `frontend/vite.config.js` | Vite build config + dev proxy | Vite |
| `.env.example` | Environment variable template | Developer reference |
| `docs/supabase_schema.sql` | PostgreSQL schema for Supabase | Supabase SQL Editor |
| `.github/workflows/ci.yml` | GitHub Actions CI pipeline | GitHub |
