// Real API client for the Coldcraft operator console.
// Talks to the live FastAPI backend under /api/v1 (Vite proxies it in dev).
// No mock data — every value rendered in the UI comes from these calls.

const BASE = import.meta.env.VITE_API_URL ?? "";

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`);
    this.status = status;
    this.detail = detail || `HTTP ${status}`;
  }
}

async function request(path, { method = "GET", body, allow404 = false } = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "NETWORK ERROR — IS THE API RUNNING?");
  }
  if (res.status === 404 && allow404) return null;
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    const detail = (data && (data.detail || data.message)) || `HTTP ${res.status}`;
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

const V1 = "/api/v1";

export const api = {
  // Dashboard
  getStats: () => request(`${V1}/stats`),

  // Campaigns (list endpoint returns a bare array)
  listCampaigns: ({ status = "", limit = 25, offset = 0 } = {}) => {
    const q = new URLSearchParams();
    if (status) q.set("status", status);
    q.set("limit", limit);
    q.set("offset", offset);
    return request(`${V1}/campaigns?${q.toString()}`);
  },
  getCampaign: (id) => request(`${V1}/campaigns/${id}`),
  getCampaignEvents: (id) => request(`${V1}/campaigns/${id}/events`),
  approveCampaign: (id) => request(`${V1}/campaigns/${id}/approve`, { method: "POST" }),
  sendCampaign: (id) => request(`${V1}/campaigns/${id}/send`, { method: "POST" }),
  scheduleFollowups: (id) => request(`${V1}/campaigns/${id}/followups`, { method: "POST" }),
  recordReply: (id, body) => request(`${V1}/campaigns/${id}/reply`, { method: "POST", body }),

  // Compose
  createDraft: (body) => request(`${V1}/drafts`, { method: "POST", body }),

  // Jobs
  listJobs: ({ company = "", limit = 25, offset = 0 } = {}) => {
    const q = new URLSearchParams();
    if (company) q.set("company", company);
    q.set("limit", limit);
    q.set("offset", offset);
    return request(`${V1}/jobs?${q.toString()}`);
  },
  scrapeJobs: (body) => request(`${V1}/jobs/scrape`, { method: "POST", body }),
  deleteJobs: (ids) => request(`${V1}/jobs/delete`, { method: "POST", body: { ids } }),

  // Intel
  generateIntel: (body) => request(`${V1}/intel/reports`, { method: "POST", body }),
  getIntel: (company) => request(`${V1}/intel/reports/${encodeURIComponent(company)}`, { allow404: true }),

  // Settings (config/profile may 404 before first save)
  getConfig: () => request(`${V1}/config`, { allow404: true }),
  saveConfig: (body) => request(`${V1}/config`, { method: "PUT", body }),
  getProfile: () => request(`${V1}/profile`, { allow404: true }),
  saveProfile: (body) => request(`${V1}/profile`, { method: "PUT", body }),
  getPolicies: () => request(`${V1}/policies`),
  savePolicies: (body) => request(`${V1}/policies`, { method: "PUT", body }),
  getFeatures: () => request(`${V1}/features`),
  saveFeatures: (body) => request(`${V1}/features`, { method: "PUT", body }),
  getIntegrations: () => request(`${V1}/integrations`),
  saveIntegrations: (body) => request(`${V1}/integrations`, { method: "PUT", body }),

  // Provider API keys (LLM + scraper) — status only on GET; keys write-only.
  getProviders: () => request(`${V1}/providers`),
  setProvider: (body) => request(`${V1}/providers`, { method: "PUT", body }),

  // Resumes / cover letters (LaTeX docs)
  listResumes: (kind = "") => request(`${V1}/resumes${kind ? `?kind=${kind}` : ""}`),
  getResume: (id) => request(`${V1}/resumes/${id}`),
  createResume: (body) => request(`${V1}/resumes`, { method: "POST", body }),
  updateResume: (id, body) => request(`${V1}/resumes/${id}`, { method: "PUT", body }),
  deleteResume: (id) => request(`${V1}/resumes/${id}`, { method: "DELETE" }),
  // compile returns a PDF Blob; throws ApiError({detail, log}) on failure
  compileLatex: (latex_source) => compilePdf(`${V1}/resumes/compile`, { latex_source }),
  compileResume: (id) => compilePdf(`${V1}/resumes/${id}/compile`, undefined),
  // AI: generate from a job description (grounded on stored resumes) + auto-fix
  generateResume: (body) => request(`${V1}/resumes/generate`, { method: "POST", body }),
  fixLatex: (latex_source) => request(`${V1}/resumes/fix`, { method: "POST", body: { latex_source } }),
};

async function compilePdf(path, body) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "NETWORK ERROR — IS THE API RUNNING?");
  }
  if (res.ok) return res.blob();
  let data = null;
  try { data = await res.json(); } catch { /* */ }
  const detail = data && data.detail;
  const err = new ApiError(res.status, (detail && detail.message) || (typeof detail === "string" ? detail : `HTTP ${res.status}`));
  err.log = (detail && detail.log) || "";
  throw err;
}
