import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from starlette.requests import Request

from app.api.routes import create_application, get_applications, update_application
from app.main import app
from app.schemas import ApplicationCreate, ApplicationStatusUpdate
from app.storage.json_store import JsonStore


class ApplicationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.original_store = app.state.store
        self.store = JsonStore(Path(self.temp_dir.name))
        app.state.store = self.store
        self.request = Request({"type": "http", "app": app, "headers": []})
        self.store.write("jobs.json", [{
            "id": "test-job", "title": "Junior Python Developer", "company": "Example",
            "location": "Bengaluru, India", "experience_required": "0 years", "skills": ["Python"],
            "description": "Build software", "source_url": "https://example.com/jobs/1",
            "apply_url": "https://example.com/jobs/1/apply", "workplace_type": "remote", "source": "test",
        }])

    def tearDown(self):
        app.state.store = self.original_store
        self.temp_dir.cleanup()

    def test_duplicate_tracking_returns_one_application(self):
        first = create_application(ApplicationCreate(job_id="test-job"), self.request)
        second = create_application(ApplicationCreate(job_id="test-job"), self.request)
        self.assertEqual(first.id, second.id)
        self.assertEqual(len(get_applications(self.request)), 1)
        self.assertEqual(first.status, "To submit")
        self.assertIsNone(first.applied_at)

    def test_status_and_applied_date_are_consistent_and_idempotent(self):
        created = create_application(ApplicationCreate(job_id="test-job"), self.request)
        updated = lambda status: update_application(created.id, ApplicationStatusUpdate(status=status), self.request)
        applied = updated("Applied")
        first_applied_at = applied.applied_at
        self.assertIsNotNone(first_applied_at)

        repeated = updated("Applied")
        self.assertEqual(repeated.applied_at, first_applied_at)

        interview = updated("Interview")
        self.assertEqual(interview.applied_at, first_applied_at)
        reset = updated("To submit")
        self.assertIsNone(reset.applied_at)

    def test_invalid_job_status_and_missing_application_return_errors(self):
        with self.assertRaises(HTTPException) as missing_job:
            create_application(ApplicationCreate(job_id="missing"), self.request)
        self.assertEqual(missing_job.exception.status_code, 404)
        with self.assertRaises(HTTPException) as missing_app:
            update_application("missing", ApplicationStatusUpdate(status="Applied"), self.request)
        self.assertEqual(missing_app.exception.status_code, 404)
        with self.assertRaises(ValueError):
            ApplicationStatusUpdate(status="Maybe")


if __name__ == "__main__":
    unittest.main()
