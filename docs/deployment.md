# 🚀 Deployment Guide

This guide walks you through deploying the full stack application to a production environment:
- **Frontend**: Vercel (Interactive UI)
- **Backend**: Railway (FastAPI Python Service)
- **Database**: Supabase (PostgreSQL)

---

## 🏗️ Prerequisites

Ensure you have accounts on:
1. [GitHub](https://github.com) (Commit this code first!)
2. [Vercel](https://vercel.com)
3. [Railway](https://railway.app)
4. [Supabase](https://supabase.com)

---

## 1. Database Setup (Supabase)

1. **Create Project**: Go to Supabase -> New Project -> Enter Name and Password.
2. **Get Connection URL**:
   - Go to **Project Settings** -> **Database**.
   - Copy the "Connection String" (URI) via **Transaction Mode** (Select "Supabase (Python)" dropdown typically gives robust string).
   - Format: `postgresql://postgres.[ref]:[password]@aws-0-region.pooler.supabase.com:6543/postgres`
   - Keep this safe. You will need it for Railway.

**Note**: The backend is configured to automatically create tables on first startup (`db.create_all()`). You don't need to run SQL manually.

---

## 2. Backend Deployment (Railway)

1. **New Project**: Go to Railway -> New Project -> Deploy from GitHub repo.
2. **Select Repo**: Choose this repository.
3. **Variables**: Go to the **Variables** tab and add:
   - `DATABASE_URL`: (Paste Supabase URL from step 1)
   - `CORS_ORIGINS`: `https://your-vercel-app.vercel.app` (Add `*` temporarily)
   - `PORT`: Railway sets this automatically (usually matches `8000` or random), Gunicorn listens on it.
4. **Build Command**: Railway auto-detects `requirements.txt`.
5. **Start Command**: Ensure it matches `Procfile`:
   ```bash
   gunicorn backend.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
   ```
6. **Deployment**: Railway will build and deploy. Once "Active", copy the **backend URL** (e.g., `https://smart-store-backend.up.railway.app`).

---

## 3. Frontend Deployment (Vercel)

1. **New Project**: Go to Vercel -> Add New -> Project -> Import from GitHub.
2. **Framework Preset**: Select **Vite**.
3. **Root Directory**: Select `frontend` (Since `package.json` is inside `frontend/`).
   - If Vercel asks, "Root Directory" is `frontend`.
4. **Environment Variables**:
   - `VITE_API_URL`: (Paste your Railway Backend URL, e.g., `https://smart-store-backend.up.railway.app`)
     - **Important**: Do NOT add a trailing slash `/`.
5. **Deploy**: Click Deploy.
6. **Update Backend CORS**:
   - Once successfully deployed to `https://smart-store-frontend.vercel.app`, go back to Railway Variables.
   - Update `CORS_ORIGINS` to match this exact URL to secure your API.

---

## 4. Verification

1. Open your Vercel URL.
2. Models should auto-fetch data. If empty, go to Inventory -> add a product.
3. Check Browser Console (F12) network tab to ensure calls go to Railway (not localhost).

## 🚑 Troubleshooting

- **Database Error**: Ensure `DATABASE_URL` is correct and Password handles special characters (URL encoded).
- **CORS Error**: Check Railway `CORS_ORIGINS` matches Vercel URL exactly (no trailing slash).
- **Frontend Blank**: Ensure `VITE_API_URL` is set in Vercel. 

---

## CI/CD 🔄

- **Frontend**: Pushing to `main` auto-deploys Vercel.
- **Backend**: Pushing to `main` auto-deploys Railway.
- **Database**: Schemas are auto-synced by SQLAlchemy on restart.
