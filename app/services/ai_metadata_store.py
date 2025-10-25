import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
from app.config import settings

BASE = Path(settings.STORAGE_DIR).resolve() / "metadata"

def _user_dir(user_id: str) -> Path:
    d = BASE / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d

def _image_path(user_id: str, image_id: str) -> Path:
    return _user_dir(user_id) / f"{image_id}.json"

def save_metadata(user_id: str, image_id: str, data: Dict[str, Any]) -> None:
    meta = dict(data or {})
    meta["image_id"] = image_id
    meta["updated_at"] = int(time.time())
    p = _image_path(user_id, image_id)
    p.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    append_update_event(user_id, image_id, meta)

def load_metadata(user_id: str, image_id: str) -> Optional[Dict[str, Any]]:
    p = _image_path(user_id, image_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def list_metadata(user_id: str) -> Dict[str, Dict[str, Any]]:
    d = _user_dir(user_id)
    out: Dict[str, Dict[str, Any]] = {}
    for f in d.glob("*.json"):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
            out[f.stem] = obj
        except Exception:
            continue
    return out

def append_update_event(user_id: str, image_id: str, meta: Dict[str, Any]) -> None:
    ev_path = BASE / "updates.jsonl"
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({
        "user_id": str(user_id),
        "image_id": str(image_id),
        "metadata": meta,
        "ts": int(time.time()),
    }, ensure_ascii=False)
    with ev_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")