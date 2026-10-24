import { useEffect, useRef, useState } from "react";
import { api } from "./lib/api";
import type { Application, Job, Profile, Resume } from "./types";
import { ApplicationsView } from "./components/applications/ApplicationsView";
import { JobSearchView } from "./components/jobs/JobSearchView";
import { PageHeader, Sidebar, type View } from "./components/layout/Sidebar";
import { ProfileView } from "./components/profile/ProfileView";
import { ChatView } from "./components/chat/ChatView";
import { Icon } from "./components/ui/Icon";

const blank: Profile = {
  name: "",
  email: "",
  phone: "",
  designation: "",
  title: "",
  location: "",
  preferred_location: "",
  preferred_workplace: "Any",
  skills: [],
  experience: 0,
  education: [],
  projects: [],
};
type ChatLine = { role: "user" | "assistant"; content: string; href?: string; localOnly?: boolean; showApplications?: boolean };

function App() {
  const [view, setView] = useState<View>("search");
  const mainRef = useRef<HTMLElement>(null);
  const lastView = useRef(view);
  const [profile, setProfile] = useState(blank);
  const [resume, setResume] = useState<Resume | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [chatJobs, setChatJobs] = useState<Job[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [chat, setChat] = useState<ChatLine[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mobileNav, setMobileNav] = useState(false);

  const refresh = async () => {
    try {
      const [p, r, a, j] = await Promise.all([
        api.profile(),
        api.resume(),
        api.applications(),
        api.jobs(),
      ]);
      setProfile(p);
      setResume(r);
      setApplications(a);
      setJobs(j);
      setError("");
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not connect to the backend. Start the Python API and refresh.",
      );
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void refresh();
  }, []);
  useEffect(() => {
    if (lastView.current === view) return;
    lastView.current = view;
    mainRef.current?.scrollTo({ top: 0, behavior: "smooth" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [view]);
  useEffect(() => {
    if (!mobileNav) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileNav(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [mobileNav]);

  const search = async (query: string) => {
    setLoading(true);
    setJobs([]);
    try {
      setJobs(await api.jobs(query));
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Job search failed");
    } finally {
      setLoading(false);
    }
  };
  const track = async (job: Job) => {
    try {
      await api.track(job.id);
      setApplications(await api.applications());
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not track role");
    }
  };
  const updateStatus = async (
    app: Application,
    status: Application["status"],
  ) => {
    try {
      const updated = await api.updateApplication(app.id, status);
      setApplications((old) =>
        old.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update application");
    }
  };
  const removeApplication = async (app: Application) => {
    try {
      await api.removeApplication(app.id);
      setApplications((old) => old.filter((item) => item.id !== app.id));
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not remove tracked role");
    }
  };
  const saveProfile = async (next: Profile) => {
    setBusy(true);
    try {
      const saved = await api.saveProfile(next);
      setProfile(saved);
      setError("");
      // Saving is complete as soon as the profile reaches the local API.
      // Re-rank in the background so a large catalogue cannot hold the form
      // open while recommendations are recalculated.
      void api.jobs().then(setJobs).catch((e) => {
        setError(e instanceof Error ? e.message : "Could not refresh job matches");
      });
    } finally {
      setBusy(false);
    }
  };
  const upload = async (file: File): Promise<Resume> => {
    setBusy(true);
    setLoading(true);
    setJobs([]);
    setChatJobs([]);
    setError("");
    try {
      const result = await api.upload(file);
      setResume(result);
      const [updatedProfile, matchedJobs] = await Promise.all([
        api.profile(),
        api.jobs(),
      ]);
      setProfile(updatedProfile);
      setJobs(matchedJobs);
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not process resume");
      throw e;
    } finally {
      setBusy(false);
      setLoading(false);
    }
  };
  const sendMessage = async (text: string) => {
    text = text.trim();
    if (!text || busy) return;
    const previousJobIds = chatJobs.map((job) => job.id);
    // Clear the previous search's cards as soon as a new question is sent.
    // Only the response to a job-oriented action may populate them again.
    setChatJobs([]);
    const history = [...chat, { role: "user" as const, content: text }];
    setChat(history);
    setBusy(true);
    try {
      const safeHistory = chat.filter((line) => !line.localOnly).map(({ role, content }) => ({ role, content }));
      const result = await api.chat(text, safeHistory, previousJobIds);
      const tracked = result.action === "tracked" ? result.applications?.[0] : undefined;
      setChat([...history, {
        role: "assistant",
        content: result.action === "tracked" && tracked?.status === "To submit"
          ? `${result.reply}\nAfter you submit on the employer site, tell me “I applied” if only one role is awaiting submission, or “I applied to job N” to update the right tracker entry.`
          : result.reply,
        href: tracked?.source_url,
        showApplications: result.action === "applications" || result.action === "marked_applied",
      }]);
      const jobAction = ["job_search", "tool_action", "tracked"].includes(result.action ?? "");
      setChatJobs(jobAction ? result.jobs ?? [] : []);
      setApplications(result.applications ?? (await api.applications()));
    } catch (e) {
      setChat([
        ...history,
        {
          role: "assistant",
          content: e instanceof Error ? e.message : "Assistant request failed",
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const title =
    view === "search"
      ? "Find my next role"
      : view === "profile"
        ? "Career profile"
        : view === "applications"
          ? "My applications"
          : "AI career assistant";
  const subtitle =
    view === "search"
      ? `${jobs.length} available roles, ranked by profile relevance`
      : view === "profile"
        ? resume
          ? `Resume saved · ${new Date(resume.uploaded_at).toLocaleDateString()}`
          : "Add a resume or edit your career profile"
        : view === "applications"
          ? `${applications.length} tracked applications`
          : "Ask questions, refine job results, and track your next steps";
  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      {mobileNav && (
        <button
          className="scrim"
          type="button"
          aria-label="Close navigation"
          onClick={() => setMobileNav(false)}
        />
      )}
      <div className={mobileNav ? "sidebar-wrap open" : "sidebar-wrap"}>
        <Sidebar
          view={view}
          setView={(next) => {
            setView(next);
            setMobileNav(false);
          }}
          profile={profile}
          count={applications.length}
          onClose={() => setMobileNav(false)}
        />
      </div>
      <main className="main" ref={mainRef}>
        <PageHeader title={title} subtitle={subtitle}>
          <button
            className="context-toggle"
            onClick={() => setMobileNav((open) => !open)}
            aria-label={mobileNav ? "Close navigation" : "Open navigation"}
            aria-expanded={mobileNav}
          >
            <Icon name="menu" />
          </button>
        </PageHeader>
        {error && (
          <div className="notice" role="alert">
            <span>{error}</span>
            <button className="secondary" onClick={() => void refresh()}>
              Retry
            </button>
          </div>
        )}
        {view === "search" && (
          <JobSearchView
            jobs={jobs}
              loading={loading}
              onSearch={(q) => void search(q)}
              onTrack={(job) => void track(job)}
              onProfile={() => setView("profile")}
          />
        )}
        {view === "chat" && <ChatView
          messages={chat}
            jobs={chatJobs}
          applications={applications}
          resume={resume}
          busy={busy || loading}
          onSend={sendMessage}
          onUpload={upload}
          onTrack={(job) => void track(job)}
          onResumeUploaded={(uploaded) => {
            const extracted = uploaded.extracted;
            const listDetails = (items: string[]) => items.length
              ? `${items.slice(0, 8).join("; ")}${items.length > 8 ? `; and ${items.length - 8} more` : ""}`
              : "Not detected";
            const details = [
              "Resume parsed locally. Extracted details:",
              `Name: ${extracted.name || "Not detected"}`,
              `Email: ${extracted.email || "Not detected"}`,
              `Phone: ${extracted.phone || "Not detected"}`,
              `Resume designation: ${extracted.designation || "Not detected"}`,
              `Skills (${extracted.skills.length}): ${listDetails(extracted.skills)}`,
              `Experience: ${extracted.experience} years`,
              `Education: ${listDetails(extracted.education)}`,
              `Projects: ${listDetails(extracted.projects)}`,
            ].join("\n");
            setChat((old) => [...old, {
              role: "assistant",
              content: `${details}\n\nYour target role and job preferences were left unchanged. Ask me to find matching roles whenever you’re ready.`,
              localOnly: true,
            }]);
          }}
        />}
        {view === "profile" && (
          <ProfileView
            profile={profile}
            resume={resume}
            onSave={saveProfile}
            onUpload={upload}
            busy={busy}
          />
        )}
        {view === "applications" && (
          <ApplicationsView
            applications={applications}
            onStatus={(app, status) => void updateStatus(app, status)}
            onRemove={(app) => void removeApplication(app)}
          />
        )}
      </main>
    </div>
  );
}
export default App;
