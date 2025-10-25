# Alternative ₹0 Deployment Options for PhotoVault

Since you have Neon PostgreSQL ready, here are other free deployment platforms:

## 🚀 **Option 1: Railway (Free Tier)**

### Setup:
1. Go to https://railway.app
2. Connect your GitHub account
3. Import repository
4. Set environment variables
5. Deploy automatically

JWT_SECRET=your-super-secret-jwt-key
MASTER_KEY=your-master-encryption-key
APP_ENV=prod
PORT=8000
```

### Required Files:
- `requirements.txt` ✅ (already ready)
- `Procfile`: `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`

---

## 🚀 **Option 2: Render (Free Tier)**

### Setup:
1. Go to https://render.com
2. Connect GitHub account
3. Create new Web Service
4. Point to your repository
5. Configure build and start commands

### Configuration:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment**: Same as above

---

## 🚀 **Option 3: Fly.io (Free Tier)**

### Setup:
1. Install flyctl: https://fly.io/docs/getting-started/installing-flyctl/
2. Run: `fly launch`
3. Configure fly.toml
4. Deploy: `fly deploy`

### fly.toml:
```toml
app = "photovault"

[build]
  builder = "paketobuildpacks/builder:base"

[[services]]
  http_checks = []
  internal_port = 8000
  processes = ["app"]
  protocol = "tcp"
  script_checks = []

  [services.concurrency]
    hard_limit = 25
    soft_limit = 20
    type = "connections"

  [[services.ports]]
    force_https = true
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

[env]
  PORT = "8000"
```

---

## 🚀 **Option 4: Heroku (Free Alternative - Koyeb)**

### Setup:
1. Go to https://www.koyeb.com
2. Connect GitHub
3. Deploy from repository
4. Set environment variables

---

## 📦 **Quick Setup for Any Platform**

### 1. Create Procfile:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 2. Update requirements.txt (if needed):
Add platform-specific requirements

### 3. Environment Variables (for any platform):
```env
<!-- DATABASE_URL=postgresql://neondb_owner:npg_A9gx3WksIXid@ep-purple-rice-ae4tzfq5-pooler.c-2.us-east-2.aws.neon.tech/neondb -->
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
MASTER_KEY=your-master-encryption-key-change-this-in-production
APP_ENV=prod
CORS_ORIGINS=*
EMBEDDINGS_PROVIDER=phash
ENABLE_GEOCODER=false
PORT=8000
```

## 🎯 **Recommended: Railway**

Railway is probably the easiest:
1. ✅ Free tier with good limits
2. ✅ Automatic GitHub integration
3. ✅ Simple environment variable setup
4. ✅ Supports Python/FastAPI out of the box
5. ✅ Works well with Neon PostgreSQL

Would you like me to help you set up with any of these alternatives?
