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

Gemini powers open-ended assistant questions when a key is configured. The project does not include an API key. Without one, the website, resume parsing, local job search, profile, and application tracker still run; open-ended Gemini answers are unavailable. The assistant does not fill in or submit forms on other companies' websites. It also cannot read a scanned, picture-only PDF yet; the PDF must contain selectable text.

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

Gemini is optional. Job search, resume parsing, profile editing, and application tracking work without a key. Open-ended assistant questions need a Gemini API key. The repository deliberately does not contain one.

To enable Gemini on your computer, create a file named `backend\.env` and put this line in it, replacing the example text with your own key:

```text
GEMINI_API_KEY=your_key_here
```

Keep that file private. The root `.gitignore` ignores it, so Git will not upload it. Never paste a real key into this README, a source file, a public issue, or a commit. If you do not have a key, skip this step; the rest of the app still runs. If you are reviewing someone else's submission, use a key provided through your organization's approved private secret-sharing method, or use your own Google AI Studio key. Do not expect the submitter to publish a personal key in the repository.

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

## Deploy a reviewer demo with Vercel

Vercel will host the React website. The Python API must run separately on a host that keeps its data between restarts. This backend saves the profile, application tracker, and uploaded resume to files. Vercel Functions only have a read-only filesystem plus temporary `/tmp` storage, so using that temporary folder would lose user data. Vercel's one-project multi-service feature is currently a private beta. See [Vercel's Python runtime filesystem limits](https://vercel.com/docs/functions/runtimes) and [Vercel Services availability](https://vercel.com/docs/services).

One straightforward arrangement is Vercel for the frontend and a persistent Python web service for the backend. These steps use Render as the backend example:

1. Create a backend web service from this GitHub repository. Set its **Root Directory** to `backend`, **Build Command** to `pip install -r requirements.txt`, and **Start Command** to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
2. Attach persistent storage to the backend at `/var/data`, then set `HIDANI_DATA_DIR=/var/data`. Without persistent storage, uploaded resumes and saved profile/tracker changes disappear when a service restarts or redeploys. Render persistent disks require a paid web service; check [Render's current disk documentation](https://render.com/docs/disks) before choosing a plan.
3. In the backend host's private environment settings, set `GEMINI_API_KEY` to a newly issued key and `CORS_ORIGINS` to the exact Vercel site origin, such as `https://your-project.vercel.app` (no trailing slash). Never put the Gemini key in a `VITE_` variable: Vite variables are included in browser code.
4. Import the same repository into Vercel and set **Root Directory** to `frontend`. Use the Vite defaults: install with `npm install`, build with `npm run build`, and output directory `dist`.
5. In Vercel's environment settings, add `VITE_API_BASE_URL` with the backend address ending in `/api`, for example `https://your-api.onrender.com/api`. Redeploy the frontend after adding it. The `frontend/vercel.json` file handles page refreshes on nested routes.
6. Check `https://your-api.onrender.com/api/health`, then open the Vercel site and test the profile, a sample resume upload, and the application tracker. Redeploy the backend and confirm the sample changes remain saved.

**Privacy before sharing the link:** this version has no sign-in and stores one shared profile, resume, and application tracker. Anyone who can reach the backend can read or change that data. Use only fake demo information until authentication and per-user storage are added; do not upload your personal resume to a public demo. Vercel hosting does not provide that backend access protection automatically.

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
docker run --rm -p 8001:8001 -v ai-job-assistant-data:/var/lib/ai-job-assistant ai-job-assistant
```

This starts without Gemini. To enable Gemini in Docker, first create `backend\.env` as described above, then add `--env-file backend\.env` to the `docker run` command. This reads the key from your ignored local file instead of putting it in the terminal command. Open **http://localhost:8001/**. The named Docker volume keeps profile, resume, and application data when the container stops. Building or running Docker on your computer does **not** publish the app to the internet.

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
