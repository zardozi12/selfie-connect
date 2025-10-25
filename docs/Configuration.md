# Configuration

Required `.env` values:
- `DATABASE_URL=postgres://user:3660@localhost:5432/Zubair`
- `JWT_SECRET` (min 32 chars)
- `CSRF_SECRET` (min 32 chars)
- `MASTER_KEY` (base64 32 bytes recommended)
- `APP_ENV=production` or `development`
- `CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`

Optional:
- `STORAGE_DRIVER=local`
- `STORAGE_DIR=./storage`
- `EMBEDDINGS_PROVIDER=clip` and `CLIP_MODEL=clip-ViT-B-32`
- `ENABLE_GEOCODER=true` and `GEOCODER_EMAIL`
- `METRICS_ENABLED=1` (requires `prometheus_client`)