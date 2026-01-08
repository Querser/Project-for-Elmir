#!/usr/bin/env python3
import json
from pathlib import Path

from backend.app.main import app

OUT = Path("backend/openapi.json")

def main():
    schema = app.openapi()
    OUT.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] OpenAPI written to {OUT}")

if __name__ == "__main__":
    main()
