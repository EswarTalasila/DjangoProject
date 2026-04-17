import Cookies from "js-cookie";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8080/api/v1";

async function loadApiClient() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  const importedModule = await import("@/lib/api");
  return importedModule.default;
}

describe("api client", () => {
  beforeEach(() => {
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
    Cookies.remove("user_name");
    window.history.pushState({}, "", "/dashboard");
  });

  afterEach(() => {
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
    Cookies.remove("user_name");
  });

  it("retries protected requests after a successful refresh", async () => {
    let secureAttempts = 0;
    let refreshAttempts = 0;

    server.use(
      http.get(`${API_BASE}/secure`, ({ request }) => {
        secureAttempts += 1;
        expect(request.headers.get("authorization")).toBeNull();
        if (secureAttempts === 1) return HttpResponse.json({ detail: "Unauthorized" }, { status: 401 });
        return HttpResponse.json({ ok: true });
      }),
      http.post(`${API_BASE}/auth/token-exchanges`, () => {
        refreshAttempts += 1;
        return HttpResponse.json({ message: "Session refreshed." });
      }),
    );

    const api = await loadApiClient();
    const response = await api.get("/secure");

    expect(response.status).toBe(200);
    expect(response.data).toEqual({ ok: true });
    expect(secureAttempts).toBe(2);
    expect(refreshAttempts).toBe(1);
  });

  it("does not attach bearer token on public auth/registration endpoints", async () => {
    server.use(
      http.post(`${API_BASE}/auth/sessions`, ({ request }) => {
        if (!request.headers.get("authorization")) {
          return HttpResponse.json({ ok: true });
        }
        return HttpResponse.json({ detail: "Authorization header should be absent" }, { status: 400 });
      }),
    );

    const api = await loadApiClient();
    const response = await api.post("/auth/sessions", {
      identifier: "teacher@example.com",
      password: "change-me",
    });

    expect(response.status).toBe(200);
    expect(response.data).toEqual({ ok: true });
  });

  it("clears user_name when refresh fails with 401", async () => {
    Cookies.set("user_name", "Teacher User");
    window.history.pushState({}, "", "/login");
    let refreshAttempts = 0;

    server.use(
      http.get(`${API_BASE}/unauthorized`, () => {
        return HttpResponse.json({ detail: "Unauthorized" }, { status: 401 });
      }),
      http.post(`${API_BASE}/auth/token-exchanges`, () => {
        refreshAttempts += 1;
        return HttpResponse.json({ detail: "Invalid refresh token." }, { status: 401 });
      }),
    );

    const api = await loadApiClient();
    await expect(api.get("/unauthorized")).rejects.toMatchObject({
      response: { status: 401 },
    });

    expect(refreshAttempts).toBe(1);
    expect(Cookies.get("user_name")).toBeUndefined();
  });
});
