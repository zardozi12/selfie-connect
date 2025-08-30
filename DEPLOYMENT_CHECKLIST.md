# PhotoVault Deployment Checklist (₹0 Cost)

## 🎯 Deployment Stack
- **Backend**: Deta Space (Free personal micro)
- **Database**: Neon PostgreSQL (Free tier with pgvector)
- **Storage**: Deta Drive (Free tier)
- **Total Cost**: ₹0

## ✅ Pre-Deployment Checklist

### 1. Create Accounts
- [ ] **Neon Account**: Sign up at https://neon.tech
  - [ ] Create a project
  - [ ] Create a database 
  - [ ] Copy PostgreSQL connection string
  - [ ] Enable pgvector: `CREATE EXTENSION IF NOT EXISTS vector;`

- [ ] **Deta Space Account**: Sign up at https://deta.space
  - [ ] Generate access token (Settings → Generate token)

### 2. Install Deta Space CLI
```bash
# Install Space CLI (check docs for your OS)
space login
# Enter your access token from Deta dashboard
```

### 3. Prepare Local Environment
- [ ] Code is ready in photovault/ folder
- [ ] `.spaceignore` file created ✅
- [ ] `Spacefile` created ✅
- [ ] `requirements.txt` updated ✅
- [ ] Deta storage implemented ✅

## 🚀 Deployment Steps

### 1. Initialize Deta Space App
```bash
cd photovault
space new
# This creates/updates the Spacefile
```

### 2. First Deploy
```bash
space push
```

### 3. Configure Environment Variables
Set in Deta Space dashboard or via CLI:

```bash
# Required Environment Variables
DATABASE_URL=postgresql://username:password@ep-xxx.neon.tech/neondb
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
MASTER_KEY=your-master-encryption-key-change-this-in-production
APP_ENV=prod
CORS_ORIGINS=*
EMBEDDINGS_PROVIDER=phash
ENABLE_GEOCODER=false
STORAGE_DRIVER=deta
```

### 4. Test Deployment
- [ ] Health check: `GET https://<your-app>.deta.app/health`
- [ ] API docs: `https://<your-app>.deta.app/docs`
- [ ] Sign up: `POST /auth/signup`
- [ ] Upload image: `POST /images/upload`

### 5. Initialize Database
- [ ] Tables are auto-created on first startup (Tortoise ORM)
- [ ] Optional: Run vector table creation in Neon SQL Editor

## 📊 Free Tier Limits

### Neon (Database)
- ✅ 10 GB storage
- ✅ Unlimited queries
- ✅ pgvector support included
- ✅ Connection pooling

### Deta Space (App Hosting)
- ✅ Free personal micro
- ✅ Custom domains
- ✅ HTTPS included
- ✅ Auto-scaling

### Deta Drive (File Storage)
- ✅ 10 GB storage per drive
- ✅ Unlimited drives
- ✅ No bandwidth limits

## 🔧 Troubleshooting

### Common Issues
1. **Database connection fails**
   - Check Neon connection string format
   - Ensure database is active (not paused)

2. **Storage errors**
   - Verify Deta Drive permissions
   - Check file upload size limits

3. **Build fails**
   - Review .spaceignore file
   - Check requirements.txt compatibility

### Debug Commands
```bash
# Check logs
space logs

# Check status
space info

# Rebuild and redeploy
space push --force
```

## 🎉 Success Metrics

Your deployment is successful when:
- [ ] ✅ Health endpoint returns 200
- [ ] ✅ API documentation is accessible
- [ ] ✅ User can sign up and get JWT token
- [ ] ✅ Images can be uploaded and encrypted
- [ ] ✅ Files are stored in Deta Drive
- [ ] ✅ Database tables are created in Neon
- [ ] ✅ Face detection works on uploaded images

## 🔗 Important URLs

After deployment, you'll have:
- **App URL**: `https://<your-app>.deta.app`
- **API Docs**: `https://<your-app>.deta.app/docs`
- **Health Check**: `https://<your-app>.deta.app/health`
- **Neon Dashboard**: https://console.neon.tech
- **Deta Space Dashboard**: https://deta.space

## 📝 Post-Deployment

1. **Test the complete flow**:
   - Create account → Upload images → View albums → Search

2. **Monitor usage**:
   - Neon: Check database size and queries
   - Deta: Monitor storage usage and requests

3. **Optional enhancements**:
   - Add custom domain in Deta Space
   - Enable CLIP embeddings if needed
   - Set up automatic GitHub deployment

---

**Estimated deployment time**: 15-30 minutes
**Total cost**: ₹0 (completely free)
**Production ready**: Yes, with enterprise-grade security
