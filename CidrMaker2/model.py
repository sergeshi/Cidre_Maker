"""Data model and persistence helpers for Cidremaker Desktop."""
from __future__ import annotations
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

APP_VERSION = "2.4.0-py"
SCHEMA_VERSION = "2.3"
TYPES = {"classic": "Классик", "petnat": "Петнат", "still": "Тихий", "solera": "Коль Фандо"}
STATUSES = {"planned": "План", "active": "Брожение", "aging": "Выдержка", "done": "Готово", "attention": "Требует внимания"}

def load_data(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8-sig") as f:
        value = json.load(f)
    if isinstance(value, list):
        value = {"appVersion": APP_VERSION, "dataSchemaVersion": SCHEMA_VERSION, "batches": value}
    if not isinstance(value, dict) or not isinstance(value.get("batches", []), list):
        raise ValueError("Ожидается объект JSON с массивом batches.")
    value.setdefault("appVersion", APP_VERSION)
    value.setdefault("dataSchemaVersion", SCHEMA_VERSION)
    value.setdefault("batches", [])
    for batch in value["batches"]:
        if not isinstance(batch, dict):
            raise ValueError("Каждая партия должна быть JSON-объектом.")
        batch.setdefault("id", "")
        batch.setdefault("name", "(без названия)")
        batch.setdefault("type", "classic")
        batch.setdefault("status", "planned")
        batch.setdefault("stage1", {})
        batch.setdefault("stage2", {})
        batch.setdefault("stage3", {})
        batch.setdefault("stage4", {})
        batch.setdefault("stage5", {})
    return value

def save_data(path: str | Path, data: dict[str, Any]) -> None:
    """Write atomically so a crash cannot leave a half-written journal."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

def new_batch() -> dict[str, Any]:
    from datetime import date, datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    today = date.today().isoformat()
    return {
        "id": "batch-" + datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "name": "Новая партия", "code": "", "type": "classic", "status": "planned",
        "attention": False, "createdAt": now, "createdDate": today, "updatedAt": now,
        "stage1": {"date": today, "varieties": "", "region": "", "volume": 0, "brix": 0,
                   "predictedAbv": "0.00", "actualAbv": 0, "ph": 0, "ta": 0},
        "stage2": {"tempStart": 18, "yeast": "", "yeastDate": "", "startDate": "",
                   "rackingDate": "", "measurements": [], "nutrients": []},
        "stage3": {"volume": 0, "desiredPressure": 5, "bottleSize": 0.75,
                   "liqueurPerBottle": 20, "liqueurSugarConcentration": 600,
                   "cap": "Кронен-пробка", "date": "", "autolysis": "", "tastings": []},
        "stage4": {"disgorging": "", "liqueurSugar": 0, "finalCap": "Кронен-пробка",
                   "agingMonths": 9, "leesAging": False, "leesMonths": 0,
                   "batonnage": False, "batonnageSchedule": [], "finalCode": ""},
        "stage5": {"tastingDate": "", "sparkling": 0, "tasteNotes": "", "packDate": ""},
        "generalNotes": "", "tastings": [], "photos": [], "history": [], "operations": [],
        "labelImage": "", "typeHistory": []
    }

def predicted_abv(brix: Any, final_brix: Any = 0) -> float:
    try:
        return max(0.0, (float(brix) - float(final_brix)) * 0.55)
    except (TypeError, ValueError):
        return 0.0

def classic_tirage(volume_l: Any, pressure_bar: Any, bottle_l: Any, liqueur_g_l: Any) -> dict[str, float]:
    volume, pressure, bottle, concentration = map(float, (volume_l, pressure_bar, bottle_l, liqueur_g_l))
    sugar = max(0.0, volume * pressure * 4.0)
    bottles = volume / bottle if bottle > 0 else 0.0
    total_liqueur_ml = bottles * 20.0
    required_total_liqueur_l = sugar / concentration if concentration > 0 else 0.0
    return {
        "sugar_g": sugar,
        "bottles": bottles,
        "yeast_g_template": max(0.0, volume / 10.0),
        "bentonite_g_template": max(0.0, volume),
        "required_liqueur_ml_per_bottle": required_total_liqueur_l * 1000.0 / bottles if bottles > 0 else 0.0,
        "template_liqueur_ml_total": total_liqueur_ml,
    }

def batch_search_text(batch: dict[str, Any]) -> str:
    stage1 = batch.get("stage1") or {}
    return " ".join(str(x or "") for x in (
        batch.get("name"), batch.get("code"), stage1.get("varieties"),
        stage1.get("region"), batch.get("generalNotes"), batch.get("notes")
    )).casefold()

def stats(data: dict[str, Any]) -> dict[str, float]:
    batches = data.get("batches", [])
    result: dict[str, float] = {"total": len(batches), "liters": 0.0}
    for status in STATUSES:
        result[status] = 0
    for b in batches:
        status = b.get("status", "planned")
        result[status if status in STATUSES else "planned"] += 1
        try:
            result["liters"] += float((b.get("stage1") or {}).get("volume") or 0)
        except (ValueError, TypeError):
            pass
    return result

def duplicate_json(data: Any) -> str:
    return json.dumps(deepcopy(data), ensure_ascii=False, indent=2)
