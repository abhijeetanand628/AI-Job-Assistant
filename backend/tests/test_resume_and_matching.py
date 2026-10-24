import unittest
from io import BytesIO

from pypdf import PdfWriter

from app.agents.job_matcher import rank_jobs
from app.schemas import Job, Profile
from app.services.resume_parser import basic_profile, extract_text
from scripts.scrape_jobs import MAX_CATALOGUE_JOBS, normalize, select_catalogue


class ResumeAndMatchingTests(unittest.TestCase):
    def test_resume_parser_extracts_contact_skills_and_sections(self):
        profile = basic_profile("""Asha Rao
asha@example.com
+91 98765 43210
Skills: Python, React, SQL
Education
B.Tech Computer Science
Projects
Built a job matching app
""")
        self.assertEqual(profile["name"], "Asha Rao")
        self.assertEqual(profile["email"], "asha@example.com")
        self.assertIn("Python", profile["skills"])
        self.assertTrue(profile["education"])
        self.assertTrue(profile["projects"])

    def test_resume_parser_reports_unsupported_and_unreadable_input(self):
        with self.assertRaisesRegex(ValueError, "PDF or DOCX"):
            extract_text("resume.txt", b"not a resume")
        blank_pdf = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(blank_pdf)
        with self.assertRaisesRegex(ValueError, "No readable text"):
            extract_text("empty.pdf", blank_pdf.getvalue())

    def test_matching_respects_role_experience_and_country(self):
        jobs = [
            Job(id="match", title="Python Developer", company="India Co", location="Pune, India", experience_required="1 year", skills=["Python", "SQL"], description="Python role", source_url="https://example.com/1"),
            Job(id="senior", title="Senior Python Developer", company="India Co", location="Pune, India", experience_required="5 years", skills=["Python", "SQL"], description="Python role", source_url="https://example.com/2"),
            Job(id="abroad", title="Python Developer", company="Elsewhere", location="Osaka, Japan", experience_required="1 year", skills=["Python", "SQL"], description="Python role", source_url="https://example.com/3"),
            Job(id="wrong-role", title="Sales Manager", company="India Co", location="Pune, India", experience_required="1 year", skills=["Python", "SQL"], description="Python role", source_url="https://example.com/4"),
        ]
        profile = Profile(title="Python Developer", preferred_location="India", skills=["Python", "SQL"], experience=1)
        results = rank_jobs(jobs, profile)
        self.assertEqual(results[0].id, "match")
        self.assertNotIn("abroad", [job.id for job in results])
        self.assertEqual(next(job.fit_tier for job in results if job.id == "senior"), "explore")
        self.assertEqual(next(job.fit_tier for job in results if job.id == "wrong-role"), "explore")

    def test_ashby_posting_normalizes_into_catalogue_shape(self):
        row = normalize({"source": "ashby", "company": "Example", "slug": "example"}, {
            "title": "Python Engineer", "location": "Bengaluru, India", "descriptionPlain": "Python and SQL",
            "jobUrl": "https://jobs.ashbyhq.com/example/abc", "applyUrl": "https://jobs.ashbyhq.com/example/abc/application",
            "workplaceType": "Hybrid", "publishedAt": "2026-10-20T00:00:00Z", "isListed": True,
        })
        self.assertTrue(row["id"].startswith("ashby-example-"))
        self.assertEqual(row["source"], "ashby")
        self.assertEqual(row["apply_url"], "https://jobs.ashbyhq.com/example/abc/application")
        self.assertEqual(row["workplace_type"], "hybrid")

    def test_scraper_enforces_the_3000_listing_ceiling(self):
        rows = [{"id": str(i), "company": "Company", "title": f"Role {i:04d}"} for i in range(MAX_CATALOGUE_JOBS + 12)]
        selected = select_catalogue(rows)
        self.assertEqual(len(selected), MAX_CATALOGUE_JOBS)
        self.assertEqual(selected, select_catalogue(rows))


if __name__ == "__main__":
    unittest.main()
