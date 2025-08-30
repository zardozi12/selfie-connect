-- App uses a normal Tortoise model for images, and a separate raw table
-- with a pgvector column for fast similarity search.
CREATE TABLE IF NOT EXISTS image_embeddings (
    image_id UUID PRIMARY KEY REFERENCES image (id) ON DELETE CASCADE,
    embedding vector(512) NOT NULL
);
CREATE INDEX IF NOT EXISTS image_embeddings_idx ON image_embeddings USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);