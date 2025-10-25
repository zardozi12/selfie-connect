-- Create pgvector table for image embeddings
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS image_embeddings (
    image_id UUID PRIMARY KEY REFERENCES images (id) ON DELETE CASCADE,
    emb vector(512) NOT NULL
);

-- IVFFlat index for cosine similarity
CREATE INDEX IF NOT EXISTS image_embeddings_idx
ON image_embeddings USING ivfflat (emb vector_cosine_ops) WITH (lists = 100);