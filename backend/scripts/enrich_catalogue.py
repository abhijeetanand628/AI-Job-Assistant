from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.resume_parser import find_skills
from app.settings import PROJECT_ROOT


def main() -> None:
    path = PROJECT_ROOT / "backend" / "data" / "jobs.json"
    jobs = json.loads(path.read_text(encoding="utf-8"))
    total_added = 0
    still_unspecified = 0
    for job in jobs:
        searchable = f"{job.get('title', '')} {job.get('description', '')}"
        inferred = find_skills(searchable)
        existing = job.get("skills") or []
        combined = list(dict.fromkeys([*existing, *inferred]))
        total_added += len(combined) - len(existing)
        job["skills"] = combined
        if not combined:
            still_unspecified += 1
    path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated skill mentions in {len(jobs)} listings; added {total_added} tags.")
    print(f"{still_unspecified} listings still have no known skill mentioned in their source text.")


if __name__ == "__main__":
    main()
