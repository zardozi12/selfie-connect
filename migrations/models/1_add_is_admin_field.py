from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD COLUMN "is_admin" BOOL NOT NULL DEFAULT 0;
        CREATE INDEX IF NOT EXISTS "idx_users_is_admin" ON "users" ("is_admin");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" DROP COLUMN "is_admin";
    """