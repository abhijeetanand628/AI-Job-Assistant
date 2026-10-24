import { useEffect, useRef, useState, type FormEvent } from "react";
import type { Application, Job, Resume } from "../../types";
import { Icon } from "../ui/Icon";

export type ChatLine = {
  role: "user" | "assistant";
  content: string;
  href?: string;
  localOnly?: boolean;
  showApplications?: boolean;
};

export function ChatView({
  messages,
  jobs,
  applications,
  resume,
  busy,
  onSend,
  onUpload,
  onResumeUploaded,
  onTrack,
}: {
  messages: ChatLine[];
  jobs: Job[];
  applications: Application[];
  resume: Resume | null;
  busy: boolean;
  onSend: (message: string) => Promise<void>;
  onUpload: (file: File) => Promise<Resume>;
  onResumeUploaded: (resume: Resume) => void;
  onTrack: (job: Job) => void;
}) {
  const [draft, setDraft] = useState("");
  const [uploading, setUploading] = useState(false);
  const transcriptRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // Keep first render at the top of the page. Later chat updates should
    // scroll only the transcript, never the document or sticky page header.
    if (!messages.length) return;
    const transcript = transcriptRef.current;
    if (transcript) {
      transcript.scrollTo({ top: transcript.scrollHeight, behavior: "smooth" });
    }
  }, [messages, busy]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    setDraft("");
    await onSend(text);
  };

  const upload = async (file?: File) => {
    if (!file) return;
    setUploading(true);
    try {
      const result = await onUpload(file);
      onResumeUploaded(result);
    } finally {
      setUploading(false);
    }
  };

  const visibleJobs = jobs.slice(0, 12);
  return (
    <section className="assistant-page" aria-label="AI career assistant">
      <div className="assistant-intro">
        <span className="section-kicker">CAREER COPILOT</span>
        <h2>Talk through your next move</h2>
        <p>Upload your resume, refine roles in plain language, and track the ones you want to pursue.</p>
      </div>
      <div className="assistant-workspace">
        <div className="assistant-transcript" ref={transcriptRef} aria-live="polite">
          {messages.length === 0 ? (
            <div className="assistant-welcome">
              <span className="assistant-welcome-icon"><Icon name="spark" size={24} /></span>
              <h3>What kind of role are you looking for?</h3>
              <p>Your resume is parsed on this computer. Tell me what you want to find or attach it below.</p>
              <div className="prompt-suggestions">
                {["Show remote roles", "Find jobs needing React", "Show my application status"].map((prompt) => (
                  <button key={prompt} className="secondary" onClick={() => setDraft(prompt)}>{prompt}</button>
                ))}
              </div>
            </div>
          ) : messages.map((line, index) => (
            <article key={`${index}-${line.role}`} className={`assistant-message ${line.role}`}>
              <strong>{line.role === "user" ? "You" : "AI Job Assistant"}</strong>
              <p>{line.content}</p>
              {line.href && <a className="chat-action-link" href={line.href} target="_blank" rel="noreferrer">Open employer application ↗</a>}
              {line.showApplications && applications.length > 0 && <ul className="chat-status-list">{applications.map((application) => <li key={application.id}><strong>{application.job_title}</strong> at {application.company} · {application.status}{application.applied_at && ` · Applied ${new Date(application.applied_at).toLocaleDateString()}`}</li>)}</ul>}
            </article>
          ))}
          {busy && <article className="assistant-message assistant"><strong>AI Job Assistant</strong><p>Thinking…</p></article>}
        </div>
        {messages.length > 0 && visibleJobs.length > 0 && (
          <section className="assistant-results" aria-label="Recommended jobs">
            <div className="assistant-results-heading"><h3>Roles from this conversation</h3><span>{jobs.length} results · showing {visibleJobs.length}</span></div>
            <div className="assistant-job-list">
              {visibleJobs.map((job, index) => (
                <article className="assistant-job" key={job.id}>
                  <div><strong><b className="assistant-job-number">{index + 1}.</b> {job.title}</strong><span>{job.company} · {job.location}</span><small>{job.why}</small></div>
                  <div className="assistant-job-actions">
                    <span className={`fit-pill ${job.fit_tier ?? "explore"}`}>{job.fit_tier === "strong" ? "Strong fit" : job.fit_tier === "possible" ? "Possible fit" : "Explore"} · {job.match ?? 0}/99 relevance</span>
                    <button className="secondary" onClick={() => onTrack(job)}>Save</button>
                    <a href={job.apply_url || job.source_url} target="_blank" rel="noreferrer" onClick={() => onTrack(job)}>Apply ↗</a>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}
        <div className="assistant-composer-wrap">
          <div className="assistant-composer-tools">
            <label className="chat-resume-upload">
              <Icon name="paperclip" size={15} />
              {uploading ? "Reading resume…" : resume ? `Resume attached: ${resume.file_name}` : "Attach PDF or DOCX"}
              <input type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" disabled={busy || uploading} onChange={(event) => { const file = event.currentTarget.files?.[0]; event.currentTarget.value = ""; void upload(file).catch(() => undefined); }} />
            </label>
            <span>Resume content and contact details stay on this device.</span>
          </div>
          <form className="assistant-composer" onSubmit={(event) => void submit(event)}>
            <textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="Ask for jobs, refine by skill or location, or check your tracker…" aria-label="Message AI Job Assistant" rows={2} />
            <button className="primary" disabled={busy || !draft.trim()} aria-label="Send message"><Icon name="send" /></button>
          </form>
          <p className="privacy-note">Gemini receives your messages and relevant career attributes. Uploaded files and contact details are not sent to Gemini.</p>
        </div>
      </div>
    </section>
  );
}
