CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pghash";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    password_hash TEXT NOT NULL,
    dek_encrypted_b64 TEXT NOT NULL,
    face_embedding_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Images Table
CREATE TABLE images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_filename TEXT,
    content_type TEXT,
    size_bytes BIGINT,
    width INT,
    height INT,
    gps_lat DOUBLE PRECISION,
    gps_lng DOUBLE PRECISION,
    location_text TEXT,
    storage_key TEXT NOT NULL,
    thumb_storage_key TEXT,
    checksum_sha256 TEXT NOT NULL,
    phash_hex TEXT,
    embedding_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, checksum_sha256)
);

-- Albums Table
CREATE TABLE albums (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Album Images (Many-to-Many)
CREATE TABLE album_images (
    album_id UUID NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    PRIMARY KEY (album_id, image_id)
);

-- Faces Table
CREATE TABLE faces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    x INT, y INT, w INT, h INT,
    embedding_json JSONB
);

-- Folders Table
CREATE TABLE folders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES folders(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, parent_id, name)
);

-- Public Shares Table
CREATE TABLE public_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    album_id UUID NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    require_face BOOLEAN DEFAULT FALSE,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMT-- Advanced PhotoVault Database Schema
-- Run this after the basic schema is created

-- pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Image embeddings table for pgvector similarity search
CREATE TABLE IF NOT EXISTS image_embeddings (
  image_id uuid PRIMARY KEY REFERENCES "image" (id) ON DELETE CASCADE,
  emb vector(512)
);

-- Index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_image_emb ON image_embeddings USING ivfflat (emb vector_cosine_ops);

-- Public shares tracking table
CREATE TABLE IF NOT EXISTS public_shares (
  id uuid PRIMARY KEY,
  album_id uuid NOT NULL REFERENCES "album" (id) ON DELETE CASCADE,
  created_by uuid NOT NULL REFERENCES "user" (id) ON DELETE CASCADE,
  token_hash varchar(128) NOT NULL,
  scope varchar(16) NOT NULL DEFAULT 'view',
  expires_at timestamp NOT NULL,
  max_views int NULL,
  view_count int NOT NULL DEFAULT 0,
  revoked boolean NOT NULL DEFAULT false,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for share queries
CREATE INDEX IF NOT EXISTS idx_public_shares_album ON public_shares (album_id);
CREATE INDEX IF NOT EXISTS idx_public_shares_token ON public_shares (token_hash);
CREATE INDEX IF NOT EXISTS idx_public_shares_expires ON public_shares (expires_at);

-- Audit events table
CREATE TABLE IF NOT EXISTS audit_events (
  id uuid PRIMARY KEY,
  user_id uuid NULL REFERENCES "user" (id) ON DELETE SET NULL,
  action varchar(64) NOT NULL,
  subject_type varchar(32) NULL,
  subject_id uuid NULL,
  ip varchar(64) NULL,
  ua text NULL,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for audit queries
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events (action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events (created_at);

-- Add new columns to existing image table
ALTER TABLE "image"
  ADD COLUMN IF NOT EXISTS phash_hex varchar(16),
  ADD COLUMN IF NOT EXISTS thumb_storage_key varchar(1024);

-- Index for duplicate detection
CREATE INDEX IF NOT EXISTS idx_image_user_phash ON "image"(user_id, phash_hex);

-- Add admin flag to user table if not exists
ALTER TABLE "user"
  ADD COLUMN IF NOT EXISTS is_admin boolean NOT NULL DEFAULT false;

-- Index for admin queries
CREATE INDEX IF NOT EXISTS idx_user_admin ON "user"(is_admin);
