import os
import logging

log = logging.getLogger("photovault.jobs")

# Choose backend with env: JOBS_BACKEND=celery | rq | inline
JOBS_BACKEND = os.getenv("JOBS_BACKEND", "inline").lower()

def _inline_noop(name: str):
    def _fn(*args, **kwargs):
        log.info("[INLINE] %s(%s %s)", name, args, kwargs)
        return True
    return _fn

# Default inline functions (run immediately in-process)
_enqueue_thumb = _inline_noop("generate_thumbnail")
_enqueue_embs  = _inline_noop("generate_embeddings")
_enqueue_ai_tags = _inline_noop("ai_tagging")

# Try Celery
if JOBS_BACKEND == "celery":
    try:
        from app.workers.tasks import task_generate_thumbnail, task_generate_embeddings, task_ai_tagging
        def _enqueue_thumb(image_id: str, user_id: str):
            job = task_generate_thumbnail.delay(image_id, user_id)
            return job.id
        def _enqueue_embs(image_id: str, user_id: str):
            job = task_generate_embeddings.delay(image_id, user_id)
            return job.id
        def _enqueue_ai_tags(image_id: str, user_id: str):
            job = task_ai_tagging.delay(image_id, user_id)
            return job.id
        log.info("Queue backend: Celery")
    except Exception as e:
        log.warning("Celery not available (%s). Falling back to inline.", e)
        JOBS_BACKEND = "inline"

# Try RQ
if JOBS_BACKEND == "rq":
    try:
        import redis
        from rq import Queue
        from app.workers.rq_tasks import generate_thumbnail, generate_embeddings, ai_tagging
        conn = redis.from_url(os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
        q_thumbs = Queue("thumbnails", connection=conn)
        q_embs   = Queue("embeddings", connection=conn)
        q_tags   = Queue("ai_tagging", connection=conn)
        def _enqueue_thumb(image_id: str, user_id: str):
            job = q_thumbs.enqueue(generate_thumbnail, image_id, user_id)
            return job.get_id()
        def _enqueue_embs(image_id: str, user_id: str):
            job = q_embs.enqueue(generate_embeddings, image_id, user_id)
            return job.get_id()
        def _enqueue_ai_tags(image_id: str, user_id: str):
            job = q_tags.enqueue(ai_tagging, image_id, user_id)
            return job.get_id()
        log.info("Queue backend: RQ")
    except Exception as e:
        log.warning("RQ not available (%s). Falling back to inline.", e)
        JOBS_BACKEND = "inline"

def enqueue_thumbnail(image_id: str, user_id: str):
    return _enqueue_thumb(image_id, user_id)

def enqueue_embeddings(image_id: str, user_id: str):
    return _enqueue_embs(image_id, user_id)

def enqueue_ai_tagging(image_id: str, user_id: str):
    return _enqueue_ai_tags(image_id, user_id)

# Add the following functions to solve the import error
def generate_thumbnail(image_id: str, user_id: str):
    log.info(f"Generating thumbnail for image {image_id} for user {user_id}")
    # Add your thumbnail generation logic here
    pass

def generate_embeddings(image_id: str, user_id: str):
    log.info(f"Generating embeddings for image {image_id} for user {user_id}")
    # Add your embeddings generation logic here
    pass




