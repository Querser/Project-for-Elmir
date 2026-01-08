from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"

# Чтобы `import app...` работал и в обычном запуске из корня проекта
# (потому что пакет app лежит в backend/app)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Можно дополнительно подсказать окружение, если нужно
os.environ.setdefault("ENVIRONMENT", "development")

from app.main import app  # noqa: E402


def main() -> None:
    artifacts_dir = ROOT / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    spec = app.openapi()
    out_path = artifacts_dir / "openapi.json"
    out_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
