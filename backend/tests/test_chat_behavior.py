import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from app import settings
from app.agents.orchestrator import answer_chat
from app.schemas import ChatRequest, Profile


class MemoryStore:
    def __init__(self, **data):
        self.data = data
        self.reads = []

    def read(self, name, default):
        self.reads.append(name)
        return self.data.get(name, default)

    def write(self, name, value):
        self.data[name] = value


class ChatBehaviorTests(unittest.TestCase):
    def test_ats_question_gets_a_local_score_instead_of_job_results(self):
        store = MemoryStore(**{"resume.json": {"file_name": "resume.pdf"}})
        profile = Profile(name="Asha Rao", email="asha@example.com", phone="+91 98765 43210", title="Python Developer", skills=["Python", "SQL", "React", "Git", "FastAPI"], education=["B.Tech"], projects=["Job app"], designation="Developer")
        reply, jobs, _, action = answer_chat(ChatRequest(message="Tell me the ATS score of my attached resume"), profile, store)
        self.assertIn("local ATS-readiness estimate", reply)
        self.assertIn("not a score from an employer's ATS", reply)
        self.assertEqual(jobs, [])
        self.assertEqual(action, "resume_feedback")
        self.assertNotIn("jobs.json", store.reads)

    def test_ats_improvement_question_gets_actionable_advice_not_the_score_again(self):
        store = MemoryStore(**{"resume.json": {"file_name": "resume.pdf"}})
        profile = Profile(
            name="Asha Rao", email="asha@example.com", title="Frontend Developer",
            skills=["React", "TypeScript"], projects=["Portfolio"], education=["B.Tech"],
        )
        with patch.object(settings, "GEMINI_API_KEY", ""):
            reply, jobs, _, action = answer_chat(ChatRequest(message="How can I improve this ATS?"), profile, store)
        self.assertIn("no designation was detected", reply)
        self.assertIn("single-column layout", reply)
        self.assertNotIn("readiness estimate", reply)
        self.assertEqual(jobs, [])
        self.assertEqual(action, "resume_feedback")
        self.assertNotIn("jobs.json", store.reads)

    def test_ats_improvement_without_uploaded_resume_asks_for_resume(self):
        reply, jobs, _, _ = answer_chat(ChatRequest(message="How do I improve my resume ATS?"), Profile(), MemoryStore())
        self.assertIn("Upload a PDF or DOCX resume", reply)
        self.assertEqual(jobs, [])

    def test_ats_improvement_uses_gemini_for_the_actual_question(self):
        store = MemoryStore(**{"resume.json": {"file_name": "resume.pdf"}})
        response = {"candidates": [{"content": {"parts": [{"text": "Lead with measurable results from your React projects."}]}}]}
        with patch.object(settings, "GEMINI_API_KEY", "test-key"), patch("app.agents.orchestrator._generate", return_value=response):
            reply, jobs, _, action = answer_chat(ChatRequest(message="How can I improve my ATS for frontend roles?"), Profile(title="Frontend Developer"), store)
        self.assertIn("measurable results", reply)
        self.assertEqual(jobs, [])
        self.assertEqual(action, "resume_feedback")

    def test_unrelated_question_does_not_fall_back_to_openings(self):
        store = MemoryStore()
        with patch.object(settings, "GEMINI_API_KEY", ""):
            reply, jobs, _, action = answer_chat(ChatRequest(message="How do I improve my interview answers?"), Profile(), store)
        self.assertIn("Gemini is not configured", reply)
        self.assertEqual(jobs, [])
        self.assertEqual(action, "gemini_unavailable")
        self.assertNotIn("jobs.json", store.reads)

    def test_invalid_gemini_key_is_reported_without_job_fallback(self):
        store = MemoryStore()
        error = HTTPError("https://example.invalid", 401, "unauthorized", None, None)
        with patch.object(settings, "GEMINI_API_KEY", "invalid-key"), patch("app.agents.orchestrator._generate", side_effect=error):
            reply, jobs, _, action = answer_chat(ChatRequest(message="How do I improve my interview answers?"), Profile(), store)
        self.assertIn("Gemini rejected the configured API key", reply)
        self.assertEqual(jobs, [])
        self.assertEqual(action, "gemini_unavailable")


if __name__ == "__main__":
    unittest.main()
