# Database (PostgreSQL + pgvector)

PhotoVault requires PostgreSQL with the pgvector extension. SQLite and other databases are not supported.

## Setup

1) Create the database:
```bash
createdb photovault
```

2) Enable pgvector:
```bash
psql -d photovault -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

3) Create the `image_embeddings` table required for semantic search:
```sql
-- Create pgvector table for image embeddings
CREATE TABLE IF NOT EXISTS image_embeddings (
    image_id UUID PRIMARY KEY REFERENCES images (id) ON DELETE CASCADE,
    emb vector(512) NOT NULL
);

-- IVFFlat index for cosine similarity
CREATE INDEX IF NOT EXISTS image_embeddings_idx
ON image_embeddings USING ivfflat (emb vector_cosine_ops) WITH (lists = 100);
```

## Environment

Set a Postgres URL in `.env`:
- `DATABASE_URL=postgres://user:password@localhost:5432/photovault`

Install the Postgres driver:
```bash
pip install asyncpg
```