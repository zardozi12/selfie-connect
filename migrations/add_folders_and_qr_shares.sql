-- Add folders table
CREATE TABLE folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    parent_id UUID REFERENCES folders(id),
    name VARCHAR(255) NOT NULL,
    encrypted_fek TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Add folder_id to photos
ALTER TABLE photos ADD COLUMN folder_id UUID REFERENCES folders(id);

-- Backfill: create root folder per user and assign existing photos
-- (Write a script in Python or SQL for this step)

-- Add qr_shares table
CREATE TABLE qr_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    folder_id UUID REFERENCES folders(id),
    token_hash VARCHAR(128) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    permissions_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id)
);