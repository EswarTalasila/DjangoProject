import Cookies from "js-cookie";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8000/api/v1";

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
    window.history.pushState({}, "", "/dashboard");
  });

  afterEach(() => {
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
  });

  it("attaches bearer token from cookie", async () => {
    Cookies.set("access_token", "token-123");

    server.use(
      http.get(`${API_BASE}/secure`, ({ request }) => {
        if (request.headers.get("authorization") === "Bearer token-123") {
          return HttpResponse.json({ ok: true });
        }

        return HttpResponse.json({ detail: "Unauthorized" }, { status: 401 });
      }),
    );

    const api = await loadApiClient();
    const response = await api.get("/secure");

    expect(response.status).toBe(200);
    expect(response.data).toEqual({ ok: true });
  });

  it("clears auth cookies on 401 response", async () => {
    Cookies.set("access_token", "expired-token");
    Cookies.set("refresh_token", "stale-refresh");
    window.history.pushState({}, "", "/login");

    server.use(
      http.get(`${API_BASE}/unauthorized`, () => {
        return HttpResponse.json({ detail: "Unauthorized" }, { status: 401 });
      }),
    );

    const api = await loadApiClient();
    await expect(api.get("/unauthorized")).rejects.toMatchObject({
      response: { status: 401 },
    });

    expect(Cookies.get("access_token")).toBeUndefined();
    expect(Cookies.get("refresh_token")).toBeUndefined();
  });
});
