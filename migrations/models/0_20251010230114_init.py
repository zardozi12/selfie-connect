from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "id" CHAR(36) NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "name" VARCHAR(255),
    "password_hash" VARCHAR(255) NOT NULL,
    "dek_encrypted_b64" TEXT NOT NULL,
    "face_embedding_json" JSON
);
CREATE INDEX IF NOT EXISTS "idx_users_email_133a6f" ON "users" ("email");
CREATE TABLE IF NOT EXISTS "person_clusters" (
    "id" CHAR(36) NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(255) NOT NULL,
    "face_embedding_json" JSON NOT NULL,
    "representative_face_id" VARCHAR(255),
    "confidence_score" REAL NOT NULL DEFAULT 0,
    "user_id" CHAR(36) NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "images" (
    "id" CHAR(36) NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "original_filename" VARCHAR(512),
    "content_type" VARCHAR(100),
    "size_bytes" BIGINT,
    "width" INT,
    "height" INT,
    "gps_lat" REAL,
    "gps_lng" REAL,
    "location_text" VARCHAR(512),
    "storage_key" VARCHAR(1024) NOT NULL,
    "thumb_storage_key" VARCHAR(1024),
    "checksum_sha256" VARCHAR(64) NOT NULL,
    "phash_hex" VARCHAR(16),
    "embedding_json" JSON,
    "user_id" CHAR(36) NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_images_user_id_24819d" UNIQUE ("user_id", "checksum_sha256")
);
CREATE INDEX IF NOT EXISTS "idx_images_checksu_01282d" ON "images" ("checksum_sha256");
CREATE TABLE IF NOT EXISTS "albums" (
    "id" CHAR(36) NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "user_id" CHAR(36) NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_albums_user_id_9d12d4" UNIQUE ("user_id", "name")
);
CREATE TABLE IF NOT EXISTS "album_images" (
    "id" CHAR(36) NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "album_id" CHAR(36) NOT NULL REFERENCES "albums" ("id") ON DELETE CASCADE,
    "image_id" CHAR(36) NOT NULL REFERENCES "images" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_album_image_album_i_c63128" UNIQUE ("album_id", "image_id")
);
CREATE TABLE IF NOT EXISTS "faces" (
    "id" CHAR(36) NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "x" INT NOT NULL,
    "y" INT NOT NULL,
    "w" INT NOT NULL,
    "h" INT NOT NULL,
    "embedding_json" JSON,
    "image_id" CHAR(36) NOT NULL REFERENCES "images" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "public_shares" (
    "id" CHAR(36) NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "token" VARCHAR(64) NOT NULL UNIQUE,
    "expires_at" TIMESTAMP NOT NULL,
    "revoked" INT NOT NULL DEFAULT 0,
    "max_opens" INT NOT NULL DEFAULT 20,
    "opens" INT NOT NULL DEFAULT 0,
    "ip_lock" VARCHAR(64),
    "user_agent_lock" VARCHAR(256),
    "require_face" INT NOT NULL DEFAULT 1,
    "album_id" CHAR(36) NOT NULL REFERENCES "albums" ("id") ON DELETE CASCADE,
    "user_id" CHAR(36) NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_public_shar_token_9eb680" ON "public_shares" ("token");
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
