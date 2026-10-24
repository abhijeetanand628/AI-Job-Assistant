export type Profile = {
  name: string;
  email: string;
  phone: string;
  designation: string;
  title: string;
  location: string;
  preferred_location: string;
  preferred_workplace: "Any" | "Remote" | "Hybrid" | "On-site";
  skills: string[];
  experience: number;
  education: string[];
  projects: string[];
};
export type Job = {
  id: string;
  title: string;
  company: string;
  location: string;
  experience_required: string;
  skills: string[];
  description: string;
  source_url: string;
  apply_url?: string | null;
  workplace_type: string;
  source: string;
  posted_at?: string | null;
  match?: number;
  why?: string;
  fit_tier?: "strong" | "possible" | "explore";
};
export type Application = {
  id: string;
  job_id: string;
  job_title: string;
  company: string;
  status: "To submit" | "Applied" | "Interview" | "Rejected" | "Offer";
  tracked_at: string;
  applied_at: string | null;
  source_url: string;
};
export type Resume = {
  id: string;
  file_name: string;
  size: number;
  content_type: string;
  uploaded_at: string;
  extracted: Profile;
};
