import type { Application } from "../../types";
export function ApplicationsView({
  applications,
  onStatus,
  onRemove,
}: {
  applications: Application[];
  onStatus: (app: Application, status: Application["status"]) => void;
  onRemove: (app: Application) => void;
}) {
  const statuses: Application["status"][] = [
    "To submit",
    "Applied",
    "Interview",
    "Rejected",
    "Offer",
  ];
  return (
    <div className="page-view">
      <div className="page-intro">
        <div>
          <span className="section-kicker">APPLICATION TRACKER</span>
          <h2>Keep every opportunity moving</h2>
          <p>
            Track roles you saved from Job Search. Update each stage and use Open
            to visit the employer posting; applications are submitted there, not
            by this tracker.
          </p>
        </div>
      </div>
      <section className="applications-card">
        <div className="table-tools">
          <div>
            <h3>All applications</h3>
            <p>{applications.length} tracked roles</p>
          </div>
        </div>
        <div className="application-table">
          <div className="table-header">
            <span>Role</span>
            <span>Tracked</span>
            <span>Status</span>
            <span>Listing</span>
            <span />
          </div>
          {applications.map((app) => (
            <div className="table-row" key={app.id}>
              <div>
                <span className="company-logo small lavender">
                  {app.company.slice(0, 2).toUpperCase()}
                </span>
                <span>
                  <strong>{app.job_title}</strong>
                  <small>{app.company}</small>
                </span>
              </div>
            <span>
              Tracked {new Date(app.tracked_at).toLocaleDateString()}
              {app.applied_at && <small className="date-subtext">Applied {new Date(app.applied_at).toLocaleDateString()}</small>}
            </span>
              <span>
                <select
                  value={app.status}
                  onChange={(e) =>
                    onStatus(app, e.target.value as Application["status"])
                  }
                >
                  {statuses.map((status) => (
                    <option key={status}>{status}</option>
                  ))}
                </select>
              </span>
              <a href={app.source_url} target="_blank" rel="noreferrer">
                Open <span aria-hidden>↗</span>
              </a>
              <button
                className="application-remove"
                type="button"
                onClick={() => onRemove(app)}
                aria-label={`Remove ${app.job_title} from tracked applications`}
                title="Remove from tracker"
              >
                Remove
              </button>
            </div>
          ))}
          {applications.length === 0 && (
            <div className="empty-state">
              <strong>No tracked applications yet</strong>
              <p>Track a role from Job Search to see it here.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
