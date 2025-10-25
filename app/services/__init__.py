# Services module initialization
from . import encryption, vision

__all__ = ["encryption", "vision", "embeddings"]
# Avoid eager imports; submodules are imported where needed.
from . import embeddings