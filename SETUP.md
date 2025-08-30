# PhotoVault Setup Guide

## Prerequisites

1. **Python 3.9+** installed
2. **PostgreSQL** database (local or Docker)
3. **Docker** (optional, for PostgreSQL)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Database Setup

#### Option A: Using Docker (Recommended)

```bash
# Start PostgreSQL with pgvector
docker compose up -d db

# Wait for database to be ready (check with: docker compose logs db)
```

#### Option B: Local PostgreSQL

1. Install PostgreSQL locally
2. Create database: `createdb photovault`
3. Install pgvector extension: `CREATE EXTENSION vector;`

### 3. Environment Configuration

The `.env` file should contain:

```env
DATABASE_URL=postgres://postgres:postgres@localhost:5432/photovault
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
MASTER_KEY=dGVzdC1tYXN0ZXIta2V5LWZvci1kZW1vLW9ubHktY2hhbmdlLWluLXByb2R1Y3Rpb24=
```

### 4. Database Migration

```bash
# Initialize database schemas
python init_db.py

# Set up and run Aerich migrations
python setup_migrations.py
```

### 5. Start the Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8999 --reload
```

## Manual Migration Commands

If you prefer to run Aerich commands manually:

```bash
# Initialize Aerich (first time only)
aerich init -t app.db.TORTOISE_ORM

# Create initial migration
aerich init-db

# Create new migration (after model changes)
aerich migrate

# Apply pending migrations
aerich upgrade

# Check migration status
aerich inspect
```

## Troubleshooting

### Database Connection Issues

1. **"Unknown DB scheme: postgresql"**
   - Ensure `asyncpg` is installed: `pip install asyncpg`
   - Use `postgres://` instead of `postgresql://` in DATABASE_URL

2. **Connection refused**
   - Check if PostgreSQL is running
   - Verify connection details in `.env`
   - For Docker: `docker compose logs db`

3. **pgvector extension not found**
   - Install pgvector extension in PostgreSQL
   - For Docker: it's included in the pgvector image

### Application Issues

1. **Import errors**
   - Ensure all dependencies are installed
   - Check Python path and virtual environment

2. **CORS issues**
   - Verify CORS_ORIGINS in `.env`
   - Check frontend URL matches allowed origins

## Development

### Adding New Models

1. Create model in `app/models/`
2. Add to `MODELS` list in `app/db.py`
3. Create migration: `aerich migrate`
4. Apply migration: `aerich upgrade`

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `JWT_SECRET` | Secret for JWT tokens | Required |
| `CORS_ORIGINS` | Allowed CORS origins | `""` |
| `MASTER_KEY` | Base64 Fernet key for encryption | Required |
| `STORAGE_DRIVER` | Storage backend | `"local"` |
| `STORAGE_DIR` | Local storage directory | `"./storage"` |
| `EMBEDDINGS_PROVIDER` | Embedding provider | `"phash"` |
| `ENABLE_GEOCODER` | Enable geocoding | `true` |

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8999/docs
- ReDoc: http://localhost:8999/redoc
