import { useEffect, useState } from "react";
import type { Profile, Resume } from "../../types";
import { Icon } from "../ui/Icon";

export function ProfileView({
  profile,
  resume,
  onSave,
  onUpload,
  busy,
}: {
  profile: Profile;
  resume: Resume | null;
  onSave: (profile: Profile) => Promise<void>;
  onUpload: (file: File) => Promise<Resume>;
  busy: boolean;
}) {
  const [draft, setDraft] = useState(profile);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");
  useEffect(() => setDraft(profile), [profile]);
  const set = (key: keyof Profile, value: string) =>
    setDraft((old) => ({
      ...old,
      [key]:
        key === "skills"
          ? value
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          : key === "experience"
            ? Number(value)
            : value,
    }));
  const save = async () => {
    setError("");
    try {
      await onSave(draft);
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save profile");
    }
  };
  const upload = async (file?: File) => {
    if (!file) return;
    setError("");
    setUploadMessage("");
    try {
      const result = await onUpload(file);
      const extracted = result.extracted;
      const details = [
        `${extracted.skills.length} skills`,
        `${extracted.experience} years experience`,
      ];
      setUploadMessage(
        `Resume updated. Extracted ${details.join(" and ")}. Your target role and job preferences were kept.`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not process resume");
    }
  };
  const textField = (key: keyof Profile, label: string) =>
    editing ? (
      <input
        className="edit-input"
        aria-label={label}
        placeholder={
          key === "title"
            ? "Enter the role you want to pursue"
            : `Enter ${label.toLowerCase()}`
        }
        value={String(draft[key] ?? "")}
        onChange={(e) => set(key, e.target.value)}
      />
    ) : (
      <strong className="value-text">
        {String(profile[key] ?? "") ||
          (key === "title" ? "Add your target role" : "")}
      </strong>
    );
  return (
    <div className="page-view">
      <div className="page-intro">
        <div>
          <span className="section-kicker">RESUME PROFILE</span>
          <h2>Your experience, structured</h2>
          <p>Update your profile or extract details from a resume.</p>
        </div>
        {editing ? (
          <div className="edit-actions">
            <button
              className="secondary"
              onClick={() => {
                setDraft(profile);
                setEditing(false);
              }}
            >
              Cancel
            </button>
            <button
              className="primary"
              onClick={() => void save()}
              disabled={busy}
            >
              <Icon name="check" /> Save changes
            </button>
          </div>
        ) : (
          <button className="primary" onClick={() => setEditing(true)}>
            <Icon name="edit" /> Edit profile
          </button>
        )}
      </div>
      {error && (
        <p role="alert" className="upload-error">
          {error}
        </p>
      )}
      {uploadMessage && (
        <p role="status" className="upload-success">
          {uploadMessage}
        </p>
      )}
      <div className="profile-layout">
        <section className="profile-card identity-card">
          <div className="profile-card-head">
            <span className="large-avatar">
              {profile.name
                .split(/\s+/)
                .map((part) => part[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()}
            </span>
            <div className="profile-edit-fields">
              {editing ? (
                <>
                  <input
                    className="edit-input"
                    aria-label="Full name"
                    placeholder="Full name"
                    value={draft.name}
                    onChange={(e) => set("name", e.target.value)}
                  />
                  <input
                    className="edit-input"
                    aria-label="Email"
                    type="email"
                    placeholder="Email address"
                    value={draft.email}
                    onChange={(e) => set("email", e.target.value)}
                  />
                  <input
                    className="edit-input"
                    aria-label="Phone"
                    type="tel"
                    placeholder="Phone number (e.g. +91 98765 43210)"
                    value={draft.phone}
                    onChange={(e) => set("phone", e.target.value)}
                  />
                </>
              ) : (
                <>
                  <h2>{profile.name}</h2>
                  <p>{profile.title}</p>
                  <span>
                    {[profile.location, profile.email, profile.phone].filter(Boolean).join(" · ")}
                  </span>
                </>
              )}
            </div>
          </div>
          <div className="profile-grid">
            <div className="profile-section">
              <p className="eyebrow">RESUME SKILLS</p>
              {editing ? (
                <input
                  className="edit-input"
                  value={draft.skills.join(", ")}
                  onChange={(e) => set("skills", e.target.value)}
                  aria-label="Skills, comma separated"
                />
              ) : (
                <div className="skill-cloud">
                  {profile.skills.map((skill) => (
                    <span key={skill}>{skill}</span>
                  ))}
                </div>
              )}
            </div>
            <div className="profile-section">
              <p className="eyebrow">DESIGNATION DETECTED FROM RESUME</p>
              <strong className="value-text">{profile.designation || "No explicit designation label was found"}</strong>
            </div>
            <div className="profile-section">
              <p className="eyebrow">TARGET ROLE</p>
              {textField("title", "Target role")}
              <small className="field-help">Set this yourself; resume extraction never changes your target.</small>
            </div>
            <div className="profile-section">
              <p className="eyebrow">YOUR LOCATION</p>
              {textField("location", "Your location")}
            </div>
            <div className="profile-section">
              <p className="eyebrow">PREFERRED JOB LOCATION</p>
              {textField("preferred_location", "Preferred job location")}
            </div>
            <div className="profile-section">
              <p className="eyebrow">WORK PREFERENCE</p>
              {editing ? (
                <select
                  className="edit-input"
                  aria-label="Preferred work style"
                  value={draft.preferred_workplace}
                  onChange={(e) => set("preferred_workplace", e.target.value)}
                >
                  {["Any", "Remote", "Hybrid", "On-site"].map((option) => (
                    <option key={option}>{option}</option>
                  ))}
                </select>
              ) : (
                <strong className="value-text">
                  {profile.preferred_workplace}
                </strong>
              )}
            </div>
            <div className="profile-section">
              <p className="eyebrow">YEARS EXPERIENCE</p>
              {editing ? (
                <input
                  className="edit-input"
                  type="number"
                  min="0"
                  step="0.5"
                  value={draft.experience}
                  onChange={(e) => set("experience", e.target.value)}
                />
              ) : (
                <strong className="value-text">
                  {profile.experience} years
                </strong>
              )}
            </div>
          </div>
          <div className="profile-extra-sections">
            <section className="profile-section">
              <p className="eyebrow">EDUCATION FROM RESUME</p>
              {editing ? <textarea className="edit-input profile-list-edit" aria-label="Education, one entry per line" value={draft.education.join("\n")} onChange={(event) => setDraft((old) => ({ ...old, education: event.target.value.split("\n").map((item) => item.trim()).filter(Boolean) }))} /> : profile.education.length ? <ul>{profile.education.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul> : <span className="value-text">No education details extracted yet</span>}
            </section>
            <section className="profile-section">
              <p className="eyebrow">PROJECTS FROM RESUME</p>
              {editing ? <textarea className="edit-input profile-list-edit" aria-label="Projects, one entry per line" value={draft.projects.join("\n")} onChange={(event) => setDraft((old) => ({ ...old, projects: event.target.value.split("\n").map((item) => item.trim()).filter(Boolean) }))} /> : profile.projects.length ? <ul>{profile.projects.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul> : <span className="value-text">No project details extracted yet</span>}
            </section>
          </div>
        </section>
        <aside className="upload-side">
          <div className="upload-drop">
            <span>
              <Icon name="upload" />
            </span>
            <h3>{busy ? "Processing resume…" : "Upload your resume"}</h3>
            <p>PDF or DOCX, up to 10 MB. Text is extracted locally.</p>
            <label className="primary">
              Choose file
              <input
                type="file"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                disabled={busy}
                onChange={(e) => {
                  void upload(e.target.files?.[0]);
                  e.currentTarget.value = "";
                }}
              />
            </label>
            {resume && (
              <div className="saved-resume">
                <strong>{resume.file_name}</strong>
                <span>
                  {Math.ceil(resume.size / 1024)} KB ·{" "}
                  {new Date(resume.uploaded_at).toLocaleDateString()}
                </span>
                <a
                  href="/api/resumes/latest/file"
                  target="_blank"
                  rel="noreferrer"
                >
                  Download saved resume
                </a>
              </div>
            )}
          </div>
          <div className="tip-card">
            <Icon name="check" />
            <div>
              <strong>Stored on your device</strong>
              <p>
                Profile, resume, and tracker data are stored in the local Python
                backend.
              </p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
