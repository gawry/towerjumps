# 🚀 Tower Jumps Deployment Guide

This guide will help you deploy your Tower Jumps application online so others can access it.

## 🏆 Recommended: Render (Full-Stack) - FREE

Render is the easiest option for your full-stack app with generous free tiers.

### Step-by-Step Deployment:

#### 1. Prepare Your Repository
```bash
# Make sure your code is pushed to GitHub
git add .
git commit -m "Prepare for deployment"
git push origin main
```

#### 2. Deploy to Render

1. **Create Account**: Go to [render.com](https://render.com) and sign up
2. **Connect GitHub**: Link your GitHub account and repository
3. **Use Blueprint**: Render will detect the `render.yaml` file and deploy automatically!

That's it! The `render.yaml` file in your repo will:
- Deploy your FastAPI backend automatically
- Deploy your React Router v7 frontend as an SSR app automatically
- Connect them together with proper environment variables

#### 3. Access Your App
- **Frontend**: `https://towerjumps-frontend.onrender.com`
- **Backend API**: `https://towerjumps-backend.onrender.com`
- **API Docs**: `https://towerjumps-backend.onrender.com/docs`

---

## 🥈 Alternative: Vercel + Railway

For potentially better performance, split your deployment:

### Deploy Backend to Railway:
1. Go to [railway.app](https://railway.app)
2. Create new project from GitHub repo
3. **Build Command**: `uv sync`
4. **Start Command**: `uv run towerjumps-api --host 0.0.0.0`
5. **Environment Variables**:
   - `PYTHONPATH=/app/src`

### Deploy Frontend to Vercel:
```bash
cd frontend
pnpm install -g vercel
echo "VITE_API_BASE_URL=https://your-app.railway.app" > .env.production
vercel
# Note: Vercel automatically detects React Router v7 and deploys as SSR
```

---

## 🥉 Budget Option: Multiple Free Services

### Frontend: Netlify
```bash
cd frontend
echo "VITE_API_BASE_URL=https://your-backend-url.com" > .env.production
# Connect GitHub repo to Netlify - drag & drop won't work for SSR
# Netlify will detect React Router v7 and deploy with SSR support
```

### Backend: PythonAnywhere
1. Upload your backend code to [pythonanywhere.com](https://pythonanywhere.com)
2. Configure as WSGI app pointing to your FastAPI app

---

## 🔧 Configuration Notes

### Environment Variables Needed:

**Frontend (.env.production):**
```bash
VITE_API_BASE_URL=https://your-backend-domain.com
```

**Backend (Production):**
```bash
PYTHONPATH=/opt/render/project/src  # or your deployment path
```

### CORS Configuration:
Your FastAPI backend may need CORS configuration for production. If you get CORS errors, let me know!

---

## 🚀 Quick Test Commands

After deployment:
```bash
# Test backend health
curl https://your-backend-url.com/health

# Test frontend
open https://your-frontend-url.com
```

---

## 💡 Pro Tips

1. **Free Tier Limitations**:
   - Render free tier may sleep after inactivity
   - Consider paid tiers for production apps

2. **Performance**:
   - Frontend on Vercel is faster than Render static hosting
   - Railway can be faster than Render for backends

3. **Custom Domains**:
   - Most services support custom domains on paid plans
   - Great for professional presentation

---

## 🆘 Need Help?

If you encounter issues:
1. Check logs in your deployment platform dashboard
2. Verify environment variables are set correctly
3. Test your health endpoint: `/health`
4. Common issue: CORS errors (easy to fix!)

Your app should now be accessible worldwide! 🌍
