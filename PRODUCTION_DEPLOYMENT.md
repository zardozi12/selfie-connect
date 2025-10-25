{
  "username": "your_username",
  "email": "your_email@example.com",
  "password": "your_secure_password"
}# PhotoVault Production Deployment Guide
}# PhotoVault Production Deployment Guide

## 🚀 Quick Start

1. **Run the production startup script:**
   ```bash
   start_photovault_production.bat
   ```

2. **Access the application:**
   - API: http://127.0.0.1:8999
   - Swagger UI: http://127.0.0.1:8999/docs
   - ReDoc: http://127.0.0.1:8999/redoc

## 📋 Prerequisites

### System Requirements
- Python 3.11+
- PostgreSQL 13+ with pgvector extension
- 4GB+ RAM
- 10GB+ storage space

### Environment Variables
Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/photovault

# Security
JWT_SECRET=your-super-secure-jwt-secret-key-at-least-32-characters
CSRF_SECRET=your-super-secure-csrf-secret-key-at-least-32-characters
MASTER_KEY=your-master-encryption-key-base64-encoded

# Application
APP_ENV=production
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

# Storage
STORAGE_DRIVER=local
STORAGE_DIR=./storage

# AI/ML Features
EMBEDDINGS_PROVIDER=clip
CLIP_MODEL=clip-ViT-B-32
ENABLE_GEOCODER=true
GEOCODER_EMAIL=your-email@example.com
```

## 🔧 Installation Steps

### 1. Clone and Setup
```bash
cd d:\projects\photovault
pip install -r requirements.txt
```

### 2. Database Setup
```bash
# Create database
createdb photovault

# Enable pgvector extension
psql -d photovault -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations
python -m aerich upgrade
```

### 3. Generate Security Keys
```python
# Generate JWT secret
import secrets
jwt_secret = secrets.token_urlsafe(32)
print(f"JWT_SECRET={jwt_secret}")

# Generate CSRF secret
csrf_secret = secrets.token_urlsafe(32)
print(f"CSRF_SECRET={csrf_secret}")

# Generate master key
import base64
master_key = base64.b64encode(secrets.token_bytes(32)).decode()
print(f"MASTER_KEY={master_key}")
```

## 🏗️ Architecture Overview