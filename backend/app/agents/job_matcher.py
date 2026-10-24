from __future__ import annotations

import re
from functools import lru_cache
from html import unescape

from app.schemas import Job, MatchedJob, Profile
from app.services.resume_parser import find_skills

ROLE_NOISE = {"senior", "junior", "staff", "principal", "lead", "sr", "jr", "i", "ii", "iii", "iv", "remote", "hybrid", "onsite", "on-site"}
COUNTRY_ALIASES = {
    "india": ("india", "bharat"),
    "united states": ("united states", "u.s.a.", "usa", "u.s.", "us"),
    "united kingdom": ("united kingdom", "uk", "britain", "england", "scotland", "wales"),
    "canada": ("canada",),
    "australia": ("australia",),
    "japan": ("japan",),
    "ireland": ("ireland",),
    "singapore": ("singapore",),
    "germany": ("germany",),
    "france": ("france",),
    "netherlands": ("netherlands",),
    "spain": ("spain",),
    "italy": ("italy",),
    "portugal": ("portugal",),
    "sweden": ("sweden",),
    "denmark": ("denmark",),
    "switzerland": ("switzerland",),
    "poland": ("poland",),
    "romania": ("romania",),
    "mexico": ("mexico",),
    "brazil": ("brazil",),
    "israel": ("israel",),
    "south korea": ("south korea", "korea"),
    "united arab emirates": ("united arab emirates", "uae"),
}
QUERY_STOP_WORDS = {
    "show", "find", "search", "me", "my", "some", "jobs", "job", "roles", "role",
    "with", "for", "in", "at", "and", "or", "the", "a", "an", "only", "please",
    "need", "needing", "that", "match", "matches", "matching", "based", "on", "from",
    "engineer", "developer", "position", "opening", "openings", "looking", "want",
}
INDIA_PLACES = (
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal", "andaman and nicobar", "chandigarh", "dadra and nagar haveli", "daman and diu", "delhi", "jammu and kashmir", "ladakh", "lakshadweep", "puducherry", "bengaluru", "bangalore", "mumbai", "hyderabad", "pune", "chennai", "kolkata", "gurugram", "gurgaon", "noida", "new delhi", "ahmedabad", "jaipur", "kochi", "indore", "lucknow", "coimbatore", "visakhapatnam", "nagpur", "bhopal", "patna", "surat", "vadodara", "mysuru", "mysore", "thiruvananthapuram", "trivandrum",
)


def _role_terms(value: str) -> set[str]:
    normalized = value.lower()
    normalized = re.sub(r"front[\s-]*end", "frontend", normalized)
    normalized = re.sub(r"back[\s-]*end", "backend", normalized)
    normalized = re.sub(r"full[\s-]*stack", "fullstack", normalized)
    terms = set(re.findall(r"[a-z0-9+#]+", normalized))
    if terms & {"developer", "engineer", "programmer"}:
        terms.difference_update({"developer", "engineer", "programmer"})
        terms.add("devrole")
    if "ui" in terms:
        terms.add("frontend")
    return terms


def _target_role_choices(target_title: str) -> list[str]:
    choices = [part.strip() for part in re.split(r"[,;]|\bor\b", target_title, flags=re.I) if part.strip()]
    # A degree accidentally pasted into the target-role field is not a role
    # preference and should not suppress every result.
    return [
        choice
        for choice in choices
        if _role_terms(choice)
        and not re.search(r"\b(bachelor|master|degree|student|graduate|b\.?tech|m\.?tech|b\.?e\.?|m\.?e\.?)\b", choice, re.I)
    ]


def _matching_target_role(target_roles: list[str], job_title: str) -> str | None:
    job_terms = _role_terms(job_title)
    for choice in target_roles:
        required = _role_terms(choice)
        if required and required <= job_terms:
            return choice
    return None


def _preferred_country(location: str) -> str | None:
    text = location.lower()
    if any(re.search(r"(?<![a-z])" + re.escape(place) + r"(?![a-z])", text) for place in INDIA_PLACES):
        return "india"
    for country, aliases in COUNTRY_ALIASES.items():
        if any(re.search(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", text) for alias in aliases):
            return country
    return None


def _job_is_in_country(location: str, country: str) -> bool:
    text = location.lower()
    aliases = COUNTRY_ALIASES[country]
    if any(re.search(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", text) for alias in aliases):
        return True
    if country == "india":
        return any(re.search(r"(?<![a-z])" + re.escape(place) + r"(?![a-z])", text) for place in INDIA_PLACES)
    return False


def _listed_skills(job: Job) -> set[str]:
    return set(_cached_listed_skills(job.title, job.description or "", tuple(job.skills)))


@lru_cache(maxsize=5000)
def _cached_listed_skills(title: str, raw_description: str, skills: tuple[str, ...]) -> frozenset[str]:
    """Parse each static catalogue description once per backend process."""
    description = unescape(unescape(raw_description))
    description = re.sub(r"<[^>]*>", " ", description)
    searchable_text = f"{title} {description} {' '.join(skills)}".lower()
    return frozenset({skill.strip().casefold() for skill in skills} | _skill_mentions(searchable_text))


def _skill_mentions(text: str) -> set[str]:
    return {skill.casefold() for skill in find_skills(text)}


def _minimum_experience(job: Job) -> float | None:
    """Return the minimum stated years, inferring seniority only if unspecified."""
    requirement = (job.experience_required or "").strip().lower()
    if requirement and requirement not in {"not specified", "unspecified", "n/a", "unknown"}:
        numbers = re.findall(r"\d+(?:\.\d+)?", requirement)
        if numbers:
            return float(numbers[0])

    title = job.title.lower()
    if re.search(r"\b(staff|principal)\b", title):
        return 6
    if re.search(r"\b(director|vp|head)\b", title):
        return 7
    if re.search(r"\b(lead|manager|architect)\b", title):
        return 5
    if re.search(r"\b(senior|sr\.?)\b", title):
        return 3
    for level, years in (("iv", 4), ("iii", 3), ("ii", 2)):
        if re.search(rf"\b{level}\b", title):
            return float(years)
    return None


def _stated_minimum_experience(job: Job) -> float | None:
    requirement = (job.experience_required or "").strip().lower()
    if requirement and requirement not in {"not specified", "unspecified", "n/a", "unknown"}:
        numbers = re.findall(r"\d+(?:\.\d+)?", requirement)
        if numbers:
            return float(numbers[0])
    return None
def rank_jobs(jobs: list[Job], profile: Profile, query: str = "", limit: int = 50) -> list[MatchedJob]:
    query_words = {word.lower().strip(".,!?()\"'") for word in query.split()}
    terms = {word for word in query_words if len(word) > 2 and word not in QUERY_STOP_WORDS}
    requested_workplace = None
    if query_words & {"remote", "remotely"}:
        requested_workplace = "remote"
    elif query_words & {"hybrid"}:
        requested_workplace = "hybrid"
    elif query_words & {"onsite", "on-site", "office", "in-office"}:
        requested_workplace = "on-site"
    if requested_workplace:
        terms -= {"remote", "remotely", "hybrid", "onsite", "on-site", "office", "in-office"}
    requested_skills = _skill_mentions(query)
    for skill in requested_skills:
        terms -= set(re.findall(r"[a-z0-9+#]+", skill))
    role_words = {word.lower().strip(".,()") for word in profile.title.split() if len(word.strip(".,()")) > 1 and word.lower() not in ROLE_NOISE}
    location_terms = {part.strip().lower() for part in profile.preferred_location.split(",") if len(part.strip()) > 2}
    preferred_country = _preferred_country(profile.preferred_location)
    if any("bengaluru" in term or "bangalore" in term for term in location_terms):
        location_terms.update({"bengaluru", "bangalore"})
    workplace_preference = profile.preferred_workplace.lower()
    target_role_choices = _target_role_choices(profile.title)
    profile_skills = {skill.casefold() for skill in profile.skills}
    ranked = []
    for job in jobs:
        job_skills = _listed_skills(job)
        overlap = profile_skills & job_skills
        job_text = f"{job.title} {job.company} {job.location} {job.description} {' '.join(job.skills)}".lower()
        job_title_words = {word.strip(".,()") for word in job.title.lower().split() if word.lower() not in ROLE_NOISE}
        role_hits = role_words & job_title_words
        matching_role = _matching_target_role(target_role_choices, job.title) if target_role_choices else None
        query_hits = sum(term in job_text for term in terms)
        job_mentions = job_skills
        workplace = job.workplace_type.lower().replace("onsite", "on-site").replace("in-office", "on-site")
        minimum_experience = _minimum_experience(job)
        # Country preference is a hard boundary. City and state can vary within
        # the country, but do not fall back to listings in another country.
        if preferred_country and not _job_is_in_country(job.location, preferred_country):
            continue
        if terms and query_hits == 0:
            continue
        if requested_workplace and requested_workplace not in workplace:
            continue
        skill_query_match = bool(requested_skills & job_mentions) if re.search(r"\bor\b", query, re.I) else requested_skills.issubset(job_mentions)
        if requested_skills and not skill_query_match:
            continue
        if not profile_skills and not role_words and not terms:
            continue
        skill_score = round(len(overlap) / max(1, min(4, len(profile_skills))) * 45) if profile_skills else 0
        # Common developer/engineer titles are normalized together above. Other
        # listings remain visible, but rank lower when their title does not fit.
        title_score = 45 if matching_role else min(20, len(role_hits) * 10)
        query_score = min(query_hits, 4) * 5
        experience_fit = minimum_experience is not None and minimum_experience <= profile.experience
        stated_minimum = _stated_minimum_experience(job)
        experience_score = 10 if experience_fit else -20 if minimum_experience is not None else 0
        location_match = (
            _job_is_in_country(job.location, preferred_country)
            if preferred_country
            else not location_terms or any(term in job.location.lower() for term in location_terms)
        )
        workplace_match = workplace_preference == "any" or workplace == workplace_preference
        preference_score = (8 if location_match and location_terms else 0) + (6 if workplace_match and workplace_preference != "any" else 0)
        score = max(0, min(99, skill_score + title_score + query_score + experience_score + preference_score))
        skill_threshold = min(2, len(profile_skills))
        role_fit = not target_role_choices or matching_role is not None
        experience_compatible = minimum_experience is None or experience_fit
        if role_fit and experience_fit and len(overlap) >= skill_threshold:
            fit_tier = "strong"
        elif role_fit and experience_compatible and (len(overlap) > 0 or not profile_skills):
            fit_tier = "possible"
        else:
            fit_tier = "explore"
        reasons = []
        if overlap:
            reasons.append(f"{len(overlap)} of {len(profile_skills)} resume skills match: " + ", ".join(sorted(overlap)[:4]))
        if matching_role:
            reasons.append("Target role match: " + matching_role)
        elif target_role_choices:
            reasons.append("Title differs from your target role")
        if minimum_experience is not None:
            if experience_fit:
                qualifier = "Listing states" if stated_minimum is not None else "Estimated from the seniority title"
                reasons.append(f"Experience fit: {qualifier.lower()} {minimum_experience:g} years; you have {profile.experience:g}")
            else:
                reasons.append(f"Requires {minimum_experience:g} years; your profile has {profile.experience:g}")
        else:
            reasons.append("Experience requirement not specified")
        if not overlap and profile_skills:
            reasons.append("No listed skills overlap your resume")
        if len(overlap) >= skill_threshold and skill_threshold:
            reasons.append(f"Meets the {skill_threshold}-skill relevance threshold")
        elif profile_skills:
            reasons.append(f"Only {len(overlap)} resume skills found; {skill_threshold} needed for a strong fit")
        if location_terms and location_match:
            reasons.append("Preferred location match")
        elif preferred_country:
            reasons.append(f"Country preference: {preferred_country.title()}")
        elif location_terms:
            reasons.append("Location preference unavailable; shown because experience and skills fit")
        if workplace_preference != "any" and workplace_match:
            reasons.append(f"Preferred work style match: {profile.preferred_workplace}")
        elif workplace_preference != "any":
            reasons.append("Work style preference unavailable; shown because experience and skills fit")
        if query_hits:
            reasons.append("Matches your search preferences")
        if requested_skills:
            reasons.append("Listing mentions requested skills: " + ", ".join(sorted(requested_skills)))
        if requested_workplace:
            reasons.append(f"Matches requested work style: {requested_workplace.title()}")
        if not reasons:
            reasons.append("Review the role details to assess fit")
        ranked.append((fit_tier, score, len(overlap), MatchedJob(**job.model_dump(), match=score, why=". ".join(reasons) + ".", fit_tier=fit_tier)))
    tier_order = {"strong": 0, "possible": 1, "explore": 2}
    ranked.sort(key=lambda item: (tier_order[item[0]], -item[1], -item[2]))
    return [job for fit_tier, score, skill_count, job in ranked[:limit]]
