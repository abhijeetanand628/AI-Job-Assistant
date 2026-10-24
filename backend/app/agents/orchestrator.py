from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from app import settings
from app.agents.application_agent import mark_application_applied, track_application
from app.agents.job_matcher import rank_jobs
from app.schemas import ChatRequest, Job, Profile
from app.storage.json_store import JsonStore


def _gemini_reply(request: ChatRequest, profile: Profile, matches: list, applications: list, store: JsonStore, allow_tools: bool = True) -> tuple[str | None, list, list, str | None]:
    if not settings.GEMINI_API_KEY:
        return None, matches, applications, None
    tools = [{"function_declarations": [
        {"name": "search_jobs", "description": "Search the locally stored job dataset using a natural-language query.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}}, "required": ["query"]}},
        {"name": "get_application_status", "description": "Read the user's tracked job applications.", "parameters": {"type": "OBJECT", "properties": {}}},
        {"name": "track_job", "description": "Add one displayed job to the local tracker when the user asks to track or apply to it. This does not submit an employer application.", "parameters": {"type": "OBJECT", "properties": {"job_id": {"type": "STRING"}}, "required": ["job_id"]}},
    ]}]
    system_text = (
        "You are AI Job Assistant, a practical career and resume assistant. Answer the user's latest question directly and stay on that subject. "
        "Do not turn unrelated questions into job searches or recommend openings unless the user asks for jobs. "
        "Use tools only when the user asks to search jobs, track a role, or check application status. Never claim an employer form was submitted; this app only tracks roles and links to employer forms. "
        "Be clear about uncertainty. Do not invent resume facts or an official ATS score. "
        "Relevant career profile fields (no contact details or uploaded resume text): "
        + json.dumps({"designation": profile.designation, "target_role": profile.title, "skills": profile.skills, "experience": profile.experience, "education": profile.education, "projects": profile.projects, "location": profile.location})
    )
    payload = {"system_instruction": {"parts": [{"text": system_text}]}, "contents": [
        *[{"role": "model" if item.role == "assistant" else "user", "parts": [{"text": item.content}]} for item in request.history[-12:]],
        {"role": "user", "parts": [{"text": request.message}]},
    ]}
    if allow_tools:
        public_job_context = [{"id": job.id, "title": job.title, "company": job.company, "location": job.location, "skills": job.skills, "source_url": str(job.source_url)} for job in matches]
        system_text += " Available matched jobs: " + json.dumps(public_job_context) + ". Tracked applications: " + json.dumps([app.model_dump(mode="json") for app in applications])
        payload["system_instruction"]["parts"][0]["text"] = system_text
        payload["tools"] = tools
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    try:
        data = _generate(url, payload)
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        calls = [part["functionCall"] for part in parts if "functionCall" in part]
        if calls:
            responses = []
            tracked_action = False
            for call in calls:
                args = call.get("args", {})
                if call["name"] == "search_jobs":
                    matches = rank_jobs([Job(**row) for row in store.read("jobs.json", [])], profile, str(args.get("query", "")))
                    responses.append({"name": call["name"], "response": {"count": len(matches), "jobs": [{"id": j.id, "title": j.title, "company": j.company, "location": j.location, "experience_required": j.experience_required, "skills": j.skills, "match": j.match, "fit_tier": j.fit_tier, "why": j.why, "source_url": str(j.source_url)} for j in matches[:12]]}})
                elif call["name"] == "get_application_status":
                    applications = store.read("applications.json", [])
                    responses.append({"name": call["name"], "response": {"applications": applications}})
                elif call["name"] == "track_job":
                    row = next((row for row in store.read("jobs.json", []) if row["id"] == str(args.get("job_id", ""))), None)
                    if row:
                        item, created = track_application(store, Job(**row))
                        applications = store.read("applications.json", [])
                        applications = [app for app in applications if app.get("id") == item.id] + [app for app in applications if app.get("id") != item.id]
                        tracked_action = True
                        responses.append({"name": call["name"], "response": {"tracked": True, "created": created, "job_title": item.job_title, "apply_url": item.source_url}})
                    else:
                        responses.append({"name": call["name"], "response": {"tracked": False, "error": "Job ID not found"}})
            payload["contents"].append(data["candidates"][0]["content"])
            payload["contents"].append({"role": "user", "parts": [{"functionResponse": response} for response in responses]})
            data = _generate(url, payload)
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        reply = " ".join(part.get("text", "") for part in parts if part.get("text")) or None
        action = "tracked" if calls and tracked_action else "tool_action" if calls else None
        return reply, matches, applications, action
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return ("Gemini rejected the configured API key. Put a valid Google AI Studio API key in backend/.env as GEMINI_API_KEY, then restart the Python backend.", matches, applications, "gemini_unavailable")
        return ("Gemini could not answer this message right now. Please try again in a moment.", matches, applications, "gemini_unavailable")
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError):
        return None, matches, applications, None


def _generate(url: str, payload: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.loads(response.read())


def _load_jobs(store: JsonStore) -> list[Job]:
    return [Job(**row) for row in store.read("jobs.json", [])]


def _conversation_jobs(request: ChatRequest, profile: Profile, jobs: list[Job]) -> list:
    catalogue = {job.id: job for job in jobs}
    result = []
    for job_id in request.job_ids:
        job = catalogue.get(job_id)
        if job:
            ranked = rank_jobs([job], profile)
            if ranked:
                result.extend(ranked)
    return result


def _is_job_search(message: str) -> bool:
    return bool(
        re.search(r"\b(?:jobs?|job openings?|vacancies|open positions)\b", message)
        or re.search(r"\b(?:find|search|show|list|recommend|look for)\b.{0,80}\b(?:roles?|positions?|openings?)\b", message)
    )


def _ats_readiness_answer(profile: Profile, resume_uploaded: bool) -> str:
    if not resume_uploaded:
        return "Upload a PDF or DOCX resume on the Profile page first. I can then estimate ATS-readiness from the details extracted on this device."

    contact = (7 if profile.name.strip() else 0) + (7 if profile.email.strip() else 0) + (6 if profile.phone.strip() else 0)
    target = 15 if profile.title.strip() else 0
    skills = min(25, len({item.casefold() for item in profile.skills if item.strip()}) * 5)
    education = 15 if profile.education else 0
    projects = 15 if profile.projects else 0
    designation = 10 if profile.designation.strip() else 0
    score = contact + target + skills + education + projects + designation
    factors = [
        f"contact details {contact}/20",
        f"target role {target}/15",
        f"skills {skills}/25",
        f"education {education}/15",
        f"projects {projects}/15",
        f"resume designation {designation}/10",
    ]
    missing = []
    if not profile.title.strip():
        missing.append("add the target role you want to apply for")
    if len(profile.skills) < 5:
        missing.append("include relevant skills using the same wording as job descriptions")
    if not profile.education:
        missing.append("add your education details")
    if not profile.projects:
        missing.append("add projects with tools used and measurable results")
    if not profile.phone.strip():
        missing.append("add a phone number")
    advice = " Suggested improvements: " + "; ".join(missing) + "." if missing else " The parsed profile includes the main sections checked here."
    return (
        f"Your local ATS-readiness estimate is {score}/100. Breakdown: " + ", ".join(factors) + "."
        " This is a simple checklist score from the resume details parsed on this device, not a score from an employer's ATS and not a prediction of getting an interview."
        " A real match score needs a specific job description." + advice
    )


def _ats_improvement_answer(profile: Profile, resume_uploaded: bool) -> str:
    if not resume_uploaded:
        return "Upload a PDF or DOCX resume on the Profile page first. I can then point out improvements based on the details extracted from it."

    advice = []
    if not profile.designation.strip():
        advice.append("Add a clear headline directly below your name, such as the specific role you are targeting; no designation was detected in your resume.")
    if not profile.title.strip():
        advice.append("Choose one target role and tailor the resume to it instead of listing several unrelated targets.")
    if not profile.skills:
        advice.append("Add a concise skills section using the exact tools and technologies from the job description, when they accurately describe your experience.")
    if not profile.projects:
        advice.append("Add relevant projects and describe what you built, which tools you used, and the measurable result.")
    if not profile.education:
        advice.append("Add your education, course, institution, and graduation date if applicable.")
    if not profile.phone.strip():
        advice.append("Add a reliable phone number to your contact details.")
    advice.extend([
        "Rewrite experience and project bullets around actions and outcomes; include numbers where you can support them.",
        "Use standard section headings and a simple, single-column layout so resume parsers can read it reliably.",
    ])
    return (
        "To improve ATS readability, start with these changes: " + " ".join(advice)
        + " Keep every claim accurate. If you share a specific job description, I can suggest which relevant skills and experience to emphasize for that role."
    )


def answer_chat(request: ChatRequest, profile: Profile, store: JsonStore) -> tuple[str, list, list, str | None]:
    apps = store.read("applications.json", [])
    message = request.message.lower()
    confirms_submission = re.search(
        r"\b(?:i\s+(?:(?:have|already|just)\s+)*(?:applied|submitted)\b|application\s+(?:has\s+been\s+)?submitted\b|mark\s+(?:job|role)\b.*\bas\s+applied\b)",
        message,
    )
    if confirms_submission:
        conversation_matches = []
        job_number = re.search(r"\b(?:job|role)\s+#?(\d+)\b", message)
        pending = [row for row in apps if row.get("status") == "To submit"]
        if job_number:
            jobs = _load_jobs(store)
            conversation_matches = _conversation_jobs(request, profile, jobs)
            visible_jobs = conversation_matches or rank_jobs(jobs, profile)
            index = int(job_number.group(1)) - 1
            if index < 0 or index >= len(visible_jobs):
                return "I couldn't match that job number to the results in this chat. Search again and use the number shown beside the role.", conversation_matches[:12], apps, "not_found"
            job_id = visible_jobs[index].id
            if not any(row.get("job_id") == job_id for row in apps):
                return "That role isn't in your application tracker yet. Ask me to apply to that numbered role first, then confirm after submitting on the employer site.", conversation_matches[:12], apps, "not_found"
        elif len(pending) == 1:
            job_id = pending[0]["job_id"]
        elif len(pending) > 1:
            roles = "; ".join(f"{row['job_title']} at {row['company']}" for row in pending[:5])
            return f"I found multiple roles awaiting submission: {roles}. Tell me which job number you submitted so I update the right one.", conversation_matches[:12], apps, "applications"
        else:
            return "I don't see an application awaiting submission. Track a role first, then confirm here after you submit its employer form.", conversation_matches[:12], apps, "applications"
        updated, changed = mark_application_applied(store, job_id)
        if updated is None:
            return "I couldn't find that role in your tracker. Track it first, then confirm after submitting on the employer site.", conversation_matches[:12], apps, "not_found"
        state = "marked Applied" if changed else "was already marked Applied"
        return f"Thanks for confirming. {updated.job_title} at {updated.company} {state} in your tracker, with the applied date recorded.", conversation_matches[:12], store.read("applications.json", []), "marked_applied"
    # Deterministic support for the assessment's numbered "apply to job N" action.
    numbered = re.search(r"\b(?:apply|track|save)\s+(?:(?:to|for)\s+)?(?:job|role)\s+#?(\d+)\b", message)
    if numbered:
        # Numbered actions refer to the profile-ranked catalogue, not to tokens
        # in the instruction itself ("apply to job 3" is not a search query).
        jobs = _load_jobs(store)
        matches = _conversation_jobs(request, profile, jobs) or rank_jobs(jobs, profile)
        index = int(numbered.group(1)) - 1
        if 0 <= index < len(matches):
            item, created = track_application(store, matches[index])
            applications = store.read("applications.json", [])
            applications = [app for app in applications if app.get("id") == item.id] + [app for app in applications if app.get("id") != item.id]
            reply = f"{item.job_title} at {item.company} is {'now in' if created else 'already in'} your tracker with status {item.status}. Open the employer link below to complete and submit the form; I haven't submitted it for you."
            return reply, matches[:12], applications, "tracked"
        return "I couldn't find that numbered role in the current results. Search first, then tell me which result to track.", matches[:12], apps, "not_found"
    if re.search(r"\b(?:applications?|tracker|tracked applications?)\b|\b(?:job|role)\s+status\b|\bstatus\s+of\s+(?:my\s+)?(?:job|role|application)\b|\b(?:interview|application)\s+(?:status|update)\b", message):
        reply = ("No roles are in your tracker yet. Save a role from Job Search or ask me to track one." if not apps else "Here are your tracked applications. Update each status here or in My applications; tracking a role does not submit it to the employer.")
        return (reply, [], apps, "applications")

    ats_topic = bool(re.search(r"\b(?:ats|applicant tracking system|resume|cv)\b", message))
    asks_for_improvement = ats_topic and bool(re.search(r"\b(?:improv\w*|increas\w*|boost\w*|enhanc\w*|optimi[sz]\w*|fix|strengthen|better)\b", message))
    if asks_for_improvement:
        resume = store.read("resume.json", None)
        if not resume:
            return _ats_improvement_answer(profile, False), [], apps, "resume_feedback"
        # Let Gemini answer the actual improvement question using the current
        # profile and conversation. Keep a tailored local fallback for offline use.
        gemini, _, apps, action = _gemini_reply(request, profile, [], apps, store, allow_tools=False)
        if gemini:
            return gemini, [], apps, action or "resume_feedback"
        advice = _ats_improvement_answer(profile, True)
        if action == "gemini_unavailable":
            return "I couldn't reach Gemini, so here's a profile-based checklist for now. " + advice, [], apps, "resume_feedback"
        return advice, [], apps, "resume_feedback"

    asks_for_score = bool(
        re.search(r"\b(?:ats|applicant tracking system|resume score|cv score)\b", message)
        or re.search(r"\bscore\b.{0,40}\b(?:resume|cv)\b|\b(?:resume|cv)\b.{0,40}\bscore\b", message)
    )
    asks_what_ats_is = ats_topic and bool(re.search(r"\b(?:what|tell|give|check|rate|grade|evaluate|assess|how)\b", message))
    if asks_for_score or asks_what_ats_is:
        resume = store.read("resume.json", None)
        return _ats_readiness_answer(profile, bool(resume)), [], apps, "resume_feedback"

    if not _is_job_search(message):
        gemini, _, apps, action = _gemini_reply(request, profile, [], apps, store, allow_tools=False)
        if gemini:
            return gemini, [], apps, action or "answer"
        if not settings.GEMINI_API_KEY:
            reply = "Gemini is not configured, so I can't answer that in open-ended chat yet. Add a valid GEMINI_API_KEY to backend/.env and restart the backend. I can still assess your resume checklist and read your local application tracker."
        else:
            reply = "I couldn't get a reply from Gemini. Check that the GEMINI_API_KEY in backend/.env is a valid Google AI Studio API key and try again."
        return reply, [], apps, "gemini_unavailable"

    jobs = _load_jobs(store)
    matches = rank_jobs(jobs, profile, request.message)
    gemini, matches, apps, action = _gemini_reply(request, profile, matches[:12], apps, store, allow_tools=True)
    if gemini:
        if action == "gemini_unavailable":
            if matches:
                return "Gemini could not answer, so I used the local job matcher. The results are ranked against your profile.", matches[:12], apps, "job_search"
            return gemini, [], apps, action
        return gemini, matches[:12], apps, action or "job_search"
    if not jobs:
        return ("The job catalogue is empty. Run the ATS job scraper to load current public listings, then ask me to search again.", [], apps, "empty_catalog")
    if matches:
        return (f"I found {len(matches)} roles from the local job catalogue. I ranked them against your profile and search terms; the strongest matches are shown. Tell me a location, work style, or skill to narrow them down.", matches[:12], apps, "job_search")
    return ("I couldn't find a close match in the current catalogue. Try a broader title, skill, or location.", [], apps, "job_search")
