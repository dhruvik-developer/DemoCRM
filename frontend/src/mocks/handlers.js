// MSW request handlers mirroring frontend/docs/API_CONTRACT.md.
// Only what Phase 1/5 component work needs is mocked here; extend per phase.
// All paths are suffixes — the axios baseURL already includes /api (G14).

import { http, HttpResponse } from "msw";

export const handlers = [
  // ── Accounts ──────────────────────────────────────────────
  http.post("/login/", async ({ request }) => {
    const body = await request.json();
    if (!body.email || !body.password) {
      return HttpResponse.json({ detail: "Missing fields." }, { status: 400 });
    }
    return HttpResponse.json({
      message: "Login successful.",
      access_token: "mock-access-token",
      refresh_token: "mock-refresh-token",
    });
  }),

  http.post("/register/", () =>
    HttpResponse.json(
      { user_id: "00000000-0000-4000-8000-000000000001", username: "mock", email: "mock@example.com", message: "Registered." },
      { status: 201 },
    ),
  ),

  http.post("/refresh/", () =>
    HttpResponse.json({ access_token: "mock-access-token-refreshed" }),
  ),

  http.post("/logout/", () => HttpResponse.json({ message: "Logged out." })),

  http.get("/profile/:userId/", () =>
    HttpResponse.json({
      user_id: "00000000-0000-4000-8000-000000000001",
      username: "mock",
      email: "mock@example.com",
      phone_number: "1234567890",
      role: 1,
    }),
  ),

  // ── Tasks KPI ─────────────────────────────────────────────
  http.get("/tasks/kpi/", () =>
    HttpResponse.json({
      total: 0,
      open: 0,
      overdue: 0,
      today: 0,
      upcoming: 0,
      completed: 0,
      high_priority: 0,
    }),
  ),

  // ── Follow-up KPI ────────────────────────────────────────
  http.get("/followups/kpi/", () =>
    HttpResponse.json({
      total: 0,
      pending: 0,
      completed: 0,
      overdue: 0,
      today: 0,
      upcoming: 0,
      by_type: {},
    }),
  ),

  // DRF-style 401 for anything without a handler → exercises the refresh flow.
  http.get("*", ({ request }) => {
    const auth = request.headers.get("Authorization");
    if (!auth?.startsWith("Bearer mock-")) {
      return HttpResponse.json(
        { detail: "Authentication credentials were not provided." },
        { status: 401 },
      );
    }
    return HttpResponse.json({ results: [], count: 0, next: null, previous: null });
  }),
];
