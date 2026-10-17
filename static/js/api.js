// Talks to the JSON API. The session cookie rides along automatically.
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

let onUnauthorized = () => {};

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

// quiet401: for calls where a 401 is an answer (login, "who am I"), not a lost session.
export async function api(path, { method = "GET", body, quiet401 = false } = {}) {
  let response;
  try {
    response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: body ? { "content-type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Can't reach the server. Check it's running, then try again.", 0);
  }
  if (response.status === 204) return null;
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    if (response.status === 401 && !quiet401) onUnauthorized();
    throw new ApiError((data && data.error) || `Something went wrong (${response.status}).`, response.status);
  }
  return data;
}
