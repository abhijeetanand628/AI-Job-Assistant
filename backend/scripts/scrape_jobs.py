from __future__ import annotations

import json
import html
import hashlib
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.resume_parser import find_skills

BOARDS = json.loads((ROOT / "data" / "boards.json").read_text(encoding="utf-8"))
MIN_CATALOGUE_JOBS = 2200
MAX_CATALOGUE_JOBS = 3000


def fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "HidaniJobAssistant/1.0 (public ATS postings collector)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def plain(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def normalize(board, item):
    if board["source"] == "greenhouse":
        title = item.get("title", "")
        location = (item.get("location") or {}).get("name", "Unspecified")
        description = plain(item.get("content", ""))
        source_url = item.get("absolute_url", "")
        job_id = f"gh-{board['slug']}-{item.get('id')}"
        apply_url = source_url
        workplace_text = f"{location} {description}".lower()
        workplace = "remote" if "remote" in workplace_text else "hybrid" if "hybrid" in workplace_text else "on-site" if any(term in workplace_text for term in ("on-site", "onsite", "in-office")) else "unspecified"
        created = item.get("updated_at")
    elif board["source"] == "lever":
        title = item.get("text", "")
        categories = item.get("categories") or {}
        location = categories.get("location") or "Unspecified"
        description = plain(item.get("descriptionPlain") or item.get("description", ""))
        source_url = item.get("hostedUrl", "")
        apply_url = item.get("applyUrl") or source_url
        job_id = f"lever-{board['slug']}-{item.get('id')}"
        workplace = (item.get("workplaceType") or "unspecified").lower().replace("onsite", "on-site")
        created = item.get("createdAt")
    else:
        if item.get("isListed") is False:
            return {}
        title = item.get("title", "")
        location = item.get("location") or "Unspecified"
        description = plain(item.get("descriptionPlain") or item.get("descriptionHtml", ""))
        source_url = item.get("jobUrl", "")
        apply_url = item.get("applyUrl") or source_url
        stable_id = str(item.get("id") or source_url or f"{title}|{location}")
        job_id = f"ashby-{board['slug']}-{hashlib.sha256(stable_id.encode()).hexdigest()[:16]}"
        workplace = (item.get("workplaceType") or "unspecified").lower().replace("onsite", "on-site")
        created = item.get("publishedAt")
    lower = description.lower()
    skills = find_skills(lower)
    exp = re.search(r"(\d+\s*\+?\s*(?:-|to)?\s*\d*\s*years?)", lower)
    return {"id": job_id, "title": title, "company": board["company"], "location": location, "experience_required": exp.group(1) if exp else "Not specified", "skills": skills, "description": description[:12000], "source_url": source_url, "apply_url": apply_url, "workplace_type": workplace, "source": board["source"], "posted_at": str(created) if created else None}


def select_catalogue(jobs):
    """Keep the public dataset within its requested upper bound deterministically."""
    ordered = sorted(jobs, key=lambda job: (job["company"].casefold(), job["title"].casefold(), job["id"]))
    return ordered[:MAX_CATALOGUE_JOBS]


def main():
    jobs = {}
    failures = []
    for board in BOARDS:
        try:
            if board["source"] == "greenhouse":
                payload = fetch(f"https://boards-api.greenhouse.io/v1/boards/{board['slug']}/jobs?content=true")
                items = payload.get("jobs", [])
            elif board["source"] == "lever":
                items = fetch(f"https://api.lever.co/v0/postings/{board['slug']}?mode=json")
            elif board["source"] == "ashby":
                payload = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{board['slug']}")
                items = payload.get("jobs", [])
            else:
                continue
            for item in items:
                normalized = normalize(board, item)
                if normalized.get("title") and normalized.get("source_url"):
                    jobs[normalized["id"]] = normalized
            print(f"{board['company']}: {len(items)} postings")
            time.sleep(0.15)
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
            failures.append(f"{board['company']}: {exc}")
    output = select_catalogue(jobs.values())
    path = ROOT / "data" / "jobs.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(output)} real public listings to {path}")
    if failures:
        print("Some public boards could not be fetched:")
        print("\n".join(failures))
    if len(output) < MIN_CATALOGUE_JOBS:
        print(f"Warning: the current catalogue has fewer than {MIN_CATALOGUE_JOBS} listings. Check board availability or add verified board slugs; no listings are fabricated.")


if __name__ == "__main__":
    main()
