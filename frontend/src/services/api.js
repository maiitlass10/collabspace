/**
 * Central HTTP client for the CollabSpace API.
 *
 * - Sends cookies (session) automatically: same origin through the Vite proxy.
 * - Adds the CSRF token header on every write request (POST/PUT/PATCH/DELETE).
 * - Turns every failure into an ApiError with an Arabic, user-friendly message.
 */

const SAFE_METHODS = ["GET", "HEAD", "OPTIONS"];

export class ApiError extends Error {
  constructor(message, { status = 0, fieldErrors = {} } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

function readCookie(name) {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=")[1]) : null;
}

const STATUS_MESSAGES = {
  400: "يرجى مراجعة البيانات المدخلة.",
  401: "يجب تسجيل الدخول أولًا.",
  403: "ليس لديك صلاحية لتنفيذ هذا الإجراء.",
  404: "العنصر المطلوب غير موجود.",
  429: "محاولات كثيرة. انتظر قليلًا ثم حاول مرة أخرى.",
  500: "حدث خطأ في الخادم. حاول لاحقًا.",
};

/**
 * DRF error bodies look like:
 *   {"detail": "..."}                                   -> general message
 *   {"non_field_errors": ["..."]}                       -> general message
 *   {"email": ["..."], "password": ["...", "..."]}      -> per-field messages
 */
function parseErrorBody(body, status) {
  const fallback = STATUS_MESSAGES[status] || STATUS_MESSAGES[500];
  if (!body || typeof body !== "object") {
    return { message: fallback, fieldErrors: {} };
  }

  const fieldErrors = {};
  let message = null;

  for (const [key, value] of Object.entries(body)) {
    const text = Array.isArray(value) ? value.join(" ") : String(value);
    if (key === "detail" || key === "non_field_errors") {
      message = text;
    } else {
      fieldErrors[key] = text;
    }
  }

  // Rate limiting and permission errors are clearer with our own wording.
  if (status === 429 || status === 403) message = STATUS_MESSAGES[status];

  return { message: message || fallback, fieldErrors };
}

export async function apiRequest(path, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (!SAFE_METHODS.includes(method)) {
    const token = readCookie("csrftoken");
    if (token) headers["X-CSRFToken"] = token;
  }

  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      credentials: "same-origin",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("تعذّر الاتصال بالخادم. تحقّق من اتصالك بالإنترنت.");
  }

  if (response.status === 204) return null;

  let data = null;
  const isJson = response.headers.get("content-type")?.includes("application/json");
  if (isJson) {
    data = await response.json().catch(() => null);
  }

  if (!response.ok) {
    const { message, fieldErrors } = parseErrorBody(data, response.status);
    throw new ApiError(message, { status: response.status, fieldErrors });
  }
  return data;
}

export function fetchHealth() {
  return apiRequest("/api/health/");
}

/** Build a ws:// or wss:// URL on the current origin (proxied by Vite). */
export function wsUrl(path) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${path}`;
}
