# AI Job Assistant

AI Job Assistant helps a person find jobs that fit their experience and skills. It can read a resume, explain why a job may fit, and keep a list of applications.

This README explains the project in simple steps. You do not need to know how the code works to run the app.

## What the app does

1. You upload a PDF or DOCX resume.
2. The app reads the text and shows what it found, such as your name, skills, education, and projects.
3. You choose your target job title, location, and other preferences in **Profile**.
4. **Job Search** and **Assistant chat** show jobs from the included catalogue and explain how each one matches.
5. You can save a job to **Applications**. If you ask the assistant to apply, it saves the job and gives you the employer's application link.
6. After you submit the employer's form yourself, tell the assistant `I applied to job 1`. It will mark that job as **Applied** and save the date.

The assistant does not fill in or submit forms on other companies' websites. It also cannot read a scanned, picture-only PDF yet; the PDF must contain selectable text.

## The project in one picture

```text
You use the website
        ↓
The React website asks the Python API for information
        ↓
The Python API reads or saves information in JSON files
        ↓
The assistant searches jobs, reads your tracker, or prepares an application link
public job boards → scraper → jobs.json → job search
```

The **frontend** is the website you see. The **backend** is the Python program that does the work and saves information. JSON files are simple text files that hold structured data.

## Project folders

```text
Hidani/
├── frontend/     The website (React and Vite)
├── backend/      The Python API, assistant logic, and job data
├── .gitignore    Tells Git which local or private files to leave out
└── README.md     This guide
```

Useful places to look:

- `frontend/src/App.tsx` connects the website screens to the API.
- `frontend/src/components/` contains the Job Search, Assistant chat, Profile, and Applications screens.
- `frontend/src/lib/api.ts` is how the website talks to the Python API.
- `backend/app/api/routes.py` contains the API actions.
- `backend/app/agents/` contains job matching, application tracking, and assistant coordination.
- `backend/app/services/resume_parser.py` reads text from PDF and DOCX resumes.
- `backend/data/jobs.json` is the public job catalogue.
- `backend/data/profile.json`, `resume.json`, `applications.json`, and `resumes/` hold this computer's personal data. These files are ignored by Git.

## Run the app on Windows

You need:

- Node.js 20.19+ or 22.12+, which runs the website tools.
- Python 3.10+, which runs the backend.
- npm, which comes with Node.js.

Run the backend and website in **two separate PowerShell windows**. Keep both windows open while you use the app.

### 1. Set up the backend (once)

Open PowerShell in the main `Hidani` project folder and run:

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Gemini is optional: without a Gemini key, the app can still search its local job list and use its built-in assistant replies. To use Gemini, create `backend\.env` in a text editor and add `GEMINI_API_KEY=your_key_here`. Keep the key private and do not upload `.env` to GitHub. The root `.gitignore` ignores local `.env` files.

### 2. Start the backend

In the first PowerShell window, run:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Leave this window running. It is now the API server. You can see its built-in API guide at **http://127.0.0.1:8001/docs**.

### 3. Start the website

Open a second PowerShell window in the main `Hidani` folder, then run:

```powershell
Set-Location frontend
npm install
npm run dev -- --port 8444
```

Leave this window running too. Open **http://localhost:8444/** in your browser to use the app. To stop either program, click its PowerShell window and press `Ctrl+C`.

## Where information is saved

- The public jobs are in `backend/data/jobs.json`.
- Your profile, uploaded resume, and application tracker are saved in `backend/data/` on this computer.
- Resume reading happens on this computer. The uploaded file, extracted contact details, and resume summary are not sent to Gemini. Gemini does receive the messages you type and selected non-contact career details. So, do not type private details into chat if you do not want Gemini to receive them.
- The app is designed for one local user. It has no sign-in screen, so do not put it on the public internet until access protection has been added.

## How job matching works

The app compares jobs with the target role and preferences you enter, your experience, and skills found in your resume. It ranks the results and gives a short reason for each match. A listing does not have to match every resume skill. Jobs with weaker matches may still appear in an **Explore** section so useful opportunities are not hidden.

The country preference is used to keep results in that country when the location is known. Some employers do not publish an experience requirement or a clear work style; the app labels missing information instead of guessing it.

## The job catalogue

The project currently includes about **2,900 public job listings** from a curated set of **12 employer boards** across Greenhouse, Lever, and Ashby. The scraper caps the catalogue at 3,000 listings and warns if refreshed sources provide fewer than 2,200. The count changes as employers open and close roles. Each listing stores its ID, title, company, location, experience requirement when listed, skills, description, and source/application link.

The scraper gets listings from the company job-board settings in `backend/data/boards.json` and saves them to `backend/data/jobs.json`. It reads public Greenhouse, Lever, and Ashby boards. It does not make up jobs. A company board can change or become unavailable, so a refresh may return a different count.

To refresh the catalogue, run this from the main `Hidani` folder after setting up the backend:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\scrape_jobs.py
```

Run the backend checks from the main project folder with:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

They cover resume parsing, role/experience/country matching, duplicate tracking, application status dates, and API errors.

To add skill labels based on words already present in job titles and descriptions, run:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe scripts\enrich_catalogue.py
```

## Run it in Docker (optional)

Docker can package the website and backend together. Install Docker Desktop first, then run these commands from the main `Hidani` folder:

```powershell
docker build -t ai-job-assistant .
docker run --rm -p 8001:8001 -v ai-job-assistant-data:/var/lib/ai-job-assistant -e GEMINI_API_KEY=YOUR_KEY ai-job-assistant
```

Replace `YOUR_KEY` with your private Gemini key, or leave the key out to use the local fallback. Open **http://localhost:8001/**. The named Docker volume keeps profile, resume, and application data when the container stops. Building or running Docker on your computer does **not** publish the app to the internet.

## API guide (for people reading the code)

An API is a set of named actions that one program can ask another program to do. These actions are served by the Python backend:

| Action | What it does |
| --- | --- |
| `GET /api/health` | Says whether the backend is running and how many jobs it has. |
| `GET` or `PUT /api/profile` | Reads or saves your profile. |
| `GET /api/jobs` or `/api/jobs/matches` | Lists jobs or ranks them against your profile. |
| `POST /api/resumes` | Receives and reads a PDF or DOCX resume. |
| `GET /api/resumes/latest` | Reads the saved resume details. |
| `GET /api/resumes/latest/file` | Downloads the saved resume. |
| `GET` or `POST /api/applications` | Lists tracked applications or adds a job to the tracker. |
| `PATCH /api/applications/{id}` | Changes an application's status. |
| `POST /api/chat` | Sends a message to the assistant. Gemini is optional. |

## Assessment checklist

The local app, job catalogue, scraper, README, and application tracker are in the project. Before an assessment submission, the remaining owner tasks are to publish a public GitHub repository, deploy the app and provide its live link, and record the requested 3–5 minute demo. The assistant provides an application handoff; the person using it must submit the employer's form. Public job feeds do not provide access to submit forms: each employer controls its own application system and required questions. The app does not claim that opening a job page submitted a form. After submission, the user can mark the role Applied in the tracker.
