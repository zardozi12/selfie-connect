from fastapi import APIRouter
import logging

def build_router() -> APIRouter:
    router = APIRouter()
    log = logging.getLogger("routers")

    try:
        from .auth import router as auth_router
        router.include_router(auth_router)
        log.info("Loaded router: auth")
    except Exception as e:
        log.exception("Failed to load router 'auth': %s", e)

    try:
        from .api import api as api_router
        router.include_router(api_router)
        log.info("Loaded router: api")
    except Exception as e:
        log.exception("Failed to load router 'api': %s", e)

    try:
        from .health import router as health_router
        router.include_router(health_router)
        log.info("Loaded router: health")
    except Exception as e:
        log.exception("Failed to load router 'health': %s", e)

    try:
        from .persons import router as persons_router
        router.include_router(persons_router)
        log.info("Loaded router: persons")
    except Exception as e:
        log.exception("Failed to load router 'persons': %s", e)

    # Images: prefer full, else minimal
    try:
        from .images import router as images_router
        router.include_router(images_router)
        log.info("Loaded router: images")
    except Exception as e:
        log.exception("Failed to load router 'images'; trying minimal. Error: %s", e)
        try:
            from .images_minimal import router as images_minimal
            router.include_router(images_minimal)
            log.info("Loaded router: images_minimal")
        except Exception as e2:
            log.exception("Failed to load router 'images_minimal': %s", e2)

    try:
        from .sharing import router as shares_router
        router.include_router(shares_router)
        log.info("Loaded router: sharing")
    except Exception as e:
        log.exception("Failed to load router 'sharing': %s", e)

    try:
        from .albums import router as albums_router
        router.include_router(albums_router)
        log.info("Loaded router: albums")
    except Exception as e:
        log.exception("Failed to load router 'albums': %s", e)

    try:
        from .dashboard import router as dashboard_router
        router.include_router(dashboard_router)
        log.info("Loaded router: dashboard")
    except Exception as e:
        log.exception("Failed to load router 'dashboard': %s", e)

    try:
        from .search_advanced import router as search_advanced
        router.include_router(search_advanced)
        log.info("Loaded router: search_advanced")
    except Exception as e:
        log.exception("Failed to load router 'search_advanced'; trying basic. Error: %s", e)
        try:
            from .search import router as search_basic
            router.include_router(search_basic)
            log.info("Loaded router: search")
        except Exception as e2:
            log.exception("Failed to load router 'search': %s", e2)

    try:
        from .images_bulk import router as images_bulk
        router.include_router(images_bulk)
        log.info("Loaded router: images_bulk")
    except Exception as e:
        log.exception("Failed to load router 'images_bulk': %s", e)

    # Admin/public share routers (guarded)
    try:
        from .admin import admin_api
        router.include_router(admin_api)
        log.info("Loaded router: admin")
    except Exception as e:
        log.exception("Failed to load router 'admin': %s", e)

    try:
        from .admin_public import public_api
        router.include_router(public_api)
        log.info("Loaded router: admin_public")
    except Exception as e:
        log.exception("Failed to load router 'admin_public'; trying metadata. Error: %s", e)
        try:
            from .metadata import router as metadata_router
            router.include_router(metadata_router)
            log.info("Loaded router: metadata")
        except Exception as e2:
            log.exception("Failed to load router 'metadata': %s", e2)
    try:
        from .facial import router as facial_router
        router.include_router(facial_router)
        log.info("Loaded router: facial")
    except Exception as e:
        log.exception("Failed to load router 'facial': %s", e)

    try:
        from .links import router as links_router
        router.include_router(links_router)
        log.info("Loaded router: links")
    except Exception as e:
        log.exception("Failed to load router 'links': %s", e)
    return router

# Export module-level router so app.main can import it
router = build_router()