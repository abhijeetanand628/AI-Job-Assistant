import type { Application, Job, Profile, Resume } from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
const json = (value: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(value),
});
export const api = {
  profile: () => request<Profile>("/profile"),
  saveProfile: (value: Profile) =>
    request<Profile>("/profile", { ...json(value), method: "PUT" }),
  jobs: (q = "") => request<Job[]>(`/jobs/matches?q=${encodeURIComponent(q)}`),
  applications: () => request<Application[]>("/applications"),
  track: (job_id: string) =>
    request<Application>("/applications", json({ job_id })),
  updateApplication: (id: string, status: Application["status"]) =>
    request<Application>(`/applications/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }),
  removeApplication: (id: string) =>
    request<void>(`/applications/${encodeURIComponent(id)}`, { method: "DELETE" }),
  resume: () => request<Resume | null>("/resumes/latest"),
  upload: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<Resume>("/resumes", { method: "POST", body });
  },
  chat: (
    message: string,
    history: { role: "user" | "assistant"; content: string }[],
    job_ids: string[] = [],
  ) =>
    request<{
      reply: string;
      jobs: Job[];
      applications: Application[];
      action?: string;
    }>("/chat", json({ message, history, job_ids })),
  resumeFile: () => `${API_BASE}/resumes/latest/file`,
};
