import { useState } from "react";
import type { Job } from "../../types";
import { Icon } from "../ui/Icon";

function readableDescription(value: string) {
  const decode = (text: string) => text
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&amp;/gi, "&");
  const decoded = decode(decode(value));
  return decoded.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

export function JobSearchView({
  jobs,
  loading,
  onSearch,
  onTrack,
  onProfile,
}: {
  jobs: Job[];
  loading: boolean;
  onSearch: (query: string) => void;
  onTrack: (job: Job) => void;
  onProfile: () => void;
}) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Job | null>(null);
  const fitGroups = [
    { id: "strong", title: "Strong fits", hint: "The target role, estimated or stated experience, and resume skill threshold align." },
    { id: "possible", title: "Possible fits", hint: "Some key requirements align; check the role details." },
    { id: "explore", title: "Other roles to explore", hint: "These remain browsable, but may miss your role, skill, or experience preferences." },
  ].map((group) => ({ ...group, jobs: jobs.filter((job) => (job.fit_tier ?? "explore") === group.id) }))
    .filter((group) => group.jobs.length > 0);
  return (
    <div className="page-view">
      <div className="page-intro">
        <div>
          <span className="section-kicker">CAREER SEARCH</span>
          <h2>Find your next role</h2>
          <p>
            Search real listings and see how each role matches your profile.
          </p>
        </div>
      </div>
      <form
        className="search-bar"
        onSubmit={(event) => {
          event.preventDefault();
          onSearch(query);
        }}
      >
        <Icon name="search" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Try “remote React engineer” or a company name"
        />
        <button className="primary">Search jobs</button>
      </form>
      {loading ? <p className="eyebrow">LOADING JOBS…</p> : <p className="eyebrow">{jobs.length} roles · {fitGroups.find((group) => group.id === "strong")?.jobs.length ?? 0} strong fits</p>}
      {fitGroups.map((group) => <section className="fit-group" key={group.id}>
        <div className="fit-group-heading"><div><h3>{group.title}</h3><p>{group.hint}</p></div><span>{group.jobs.length}</span></div>
        <div className="job-list">
        {group.jobs.map((job) => (
          <article className="job-card" key={job.id}>
            <div className="job-card-top">
              <span className="company-logo lavender">
                {job.company.slice(0, 2).toUpperCase()}
              </span>
              <div className="job-heading">
                <h3>{job.title}</h3>
                <p>{job.company}</p>
              </div>
              {job.match != null && (
                <span className="match-badge">
                  <Icon name="spark" size={13} /> Relevance {job.match}/99
                </span>
              )}
            </div>
            <span className={`fit-pill ${job.fit_tier ?? "explore"}`}>{job.fit_tier === "strong" ? "Strong fit" : job.fit_tier === "possible" ? "Possible fit" : "Explore"}</span>
            <div className="job-meta">
              <span>
                <Icon name="pin" size={14} />{" "}
                {job.location || "Location not specified"}
              </span>
              <span>
                <Icon name="clock" size={14} />{" "}
                {job.experience_required || "Experience not specified"}
              </span>
            </div>
            <p className="job-description">
              {readableDescription(job.description).slice(0, 260)}
              {readableDescription(job.description).length > 260 ? "…" : ""}
            </p>
            <div className="skill-row">
              {job.skills.length ? job.skills.slice(0, 6).map((skill) => (
                <span key={skill}>{skill}</span>
              )) : <span>Skills not specified in listing</span>}
            </div>
            {job.why && (
              <div className="why-match">
                <Icon name="spark" size={15} />
                <p>
                  <strong>Why it matches:</strong> {job.why}
                </p>
              </div>
            )}
            <div className="job-actions">
              <button className="secondary" onClick={() => setSelected(job)}>
                View details
              </button>
              <a className="primary" href={job.apply_url || job.source_url} target="_blank" rel="noreferrer" onClick={() => onTrack(job)}>
                Apply on employer site <Icon name="external" size={14} />
              </a>
            </div>
          </article>
        ))}
        </div>
      </section>)}
      {!loading && jobs.length === 0 && <div className="empty-state"><strong>No roles matched those filters</strong><p>Try removing a skill or work-style filter, or check that the catalogue has listings in your selected country.</p><button className="secondary" onClick={onProfile}>Edit job preferences</button></div>}
      {selected && (
        <>
          <div className="modal-scrim" onClick={() => setSelected(null)} />
          <aside className="job-drawer">
            <button
              className="drawer-close"
              onClick={() => setSelected(null)}
              aria-label="Close"
            >
              <Icon name="close" />
            </button>
            <span className="company-logo large lavender">
              {selected.company.slice(0, 2).toUpperCase()}
            </span>
            <h2>{selected.title}</h2>
            <p className="drawer-company">
              {selected.company} · {selected.location}
            </p>
            <div className="drawer-section">
              <h3>About the role</h3>
              <p>{readableDescription(selected.description)}</p>
            </div>
            <div className="drawer-section">
              <h3>Skills</h3>
              <div className="skill-cloud">
                {selected.skills.map((skill) => (
                  <span key={skill}>{skill}</span>
                ))}
              </div>
            </div>
            <a
              className="secondary"
              href={selected.apply_url || selected.source_url}
              target="_blank"
              rel="noreferrer"
            >
              Open employer listing <Icon name="external" />
            </a>
            <p className="apply-note">
              Opening the employer page also saves this role to your tracker. Submit it there, then update its status to Applied in Applications.
            </p>
            <button
              className="drawer-apply"
              onClick={() => {
                onTrack(selected);
                setSelected(null);
              }}
            >
              Save this role <Icon name="check" />
            </button>
          </aside>
        </>
      )}
    </div>
  );
}
