-- 001_add_unique_and_checks.sql
-- Add unique constraint to prevent duplicate uploads
ALTER TABLE "image" ADD CONSTRAINT "uq_user_checksum" UNIQUE ("user_id","checksum_sha256");

-- Face box values between 0 and 1 (if not already present)
ALTER TABLE "face" ADD CONSTRAINT "chk_face_box"
CHECK (x >= 0 AND x <= 1 AND y >= 0 AND y <= 1 AND w >= 0 AND w <= 1 AND h >= 0 AND h <= 1);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_image_user_created ON "image"("user_id", "created_at");
CREATE INDEX IF NOT EXISTS idx_image_checksum ON "image"("checksum_sha256");
