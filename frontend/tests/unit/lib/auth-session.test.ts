import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8080/api/v1";

let mockCookieGet: ReturnType<typeof vi.fn>;

async function loadAuthSession() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  delete process.env.SERVER_PROXY_ORIGIN;

  mockCookieGet = vi.fn();
  vi.doMock("next/headers", () => ({
    cookies: vi.fn(() => Promise.resolve({ get: mockCookieGet })),
  }));
  vi.doMock("react", () => ({
    cache: (fn: unknown) => fn,
  }));

  return import("@/lib/auth-session");
}

describe("auth-session", () => {
  beforeEach(() => {
    delete process.env.SERVER_PROXY_ORIGIN;
  });

  describe("getSessionProfile", () => {
    it("returns null when no access_token cookie exists", async () => {
      const { getSessionProfile } = await loadAuthSession();
      mockCookieGet.mockReturnValue(undefined);

      const result = await getSessionProfile();

      expect(result).toBeNull();
    });

    it("returns profile on successful fetch", async () => {
      const profile = {
        id: "1",
        name: "Test User",
        username: "testuser",
        email: "test@example.com",
        role: "TEACHER",
        isStaff: false,
      };

      server.use(
        http.get(`${API_BASE}/auth/me`, () => HttpResponse.json(profile)),
      );

      const { getSessionProfile } = await loadAuthSession();
      mockCookieGet.mockReturnValue({ value: "valid-token" });

      const result = await getSessionProfile();

      expect(result).toEqual(profile);
    });

    it("returns null when response is not ok", async () => {
      server.use(
        http.get(`${API_BASE}/auth/me`, () =>
          HttpResponse.json({ detail: "Unauthorized" }, { status: 401 }),
        ),
      );

      const { getSessionProfile } = await loadAuthSession();
      mockCookieGet.mockReturnValue({ value: "expired-token" });

      const result = await getSessionProfile();

      expect(result).toBeNull();
    });

    it("returns null for invalid role", async () => {
      server.use(
        http.get(`${API_BASE}/auth/me`, () =>
          HttpResponse.json({
            id: "1",
            name: "Test",
            username: "test",
            email: null,
            role: "INVALID_ROLE",
            isStaff: false,
          }),
        ),
      );

      const { getSessionProfile } = await loadAuthSession();
      mockCookieGet.mockReturnValue({ value: "valid-token" });

      const result = await getSessionProfile();

      expect(result).toBeNull();
    });

    it("returns null when role is empty string", async () => {
      server.use(
        http.get(`${API_BASE}/auth/me`, () =>
          HttpResponse.json({
            id: "1",
            name: "Test",
            username: "test",
            email: null,
            role: "",
            isStaff: false,
          }),
        ),
      );

      const { getSessionProfile } = await loadAuthSession();
      mockCookieGet.mockReturnValue({ value: "valid-token" });

      const result = await getSessionProfile();

      expect(result).toBeNull();
    });

    it("accepts ADMIN role", async () => {
      server.use(
        http.get(`${API_BASE}/auth/me`, () =>
          HttpResponse.json({
            id: "1",
            name: "Admin",
            username: "admin",
            email: null,
            role: "ADMIN",
            isStaff: true,
          }),
        ),
      );

      const { getSessionProfile } = await loadAuthSession();
      mockCookieGet.mockReturnValue({ value: "valid-token" });

      const result = await getSessionProfile();

      expect(result).not.toBeNull();
      expect(result!.role).toBe("ADMIN");
    });

    it("accepts STUDENT role", async () => {
      server.use(
        http.get(`${API_BASE}/auth/me`, () =>
          HttpResponse.json({
            id: "2",
            name: "Student",
            username: "student",
            email: null,
            role: "STUDENT",
            isStaff: false,
          }),
        ),
      );

      const { getSessionProfile } = await loadAuthSession();
      mockCookieGet.mockReturnValue({ value: "valid-token" });

      const result = await getSessionProfile();

      expect(result).not.toBeNull();
      expect(result!.role).toBe("STUDENT");
    });

    it("accepts RESEARCHER role", async () => {
      server.use(
        http.get(`${API_BASE}/auth/me`, () =>
          HttpResponse.json({
            id: "3",
            name: "Researcher",
            username: "researcher",
            email: null,
            role: "RESEARCHER",
            isStaff: false,
          }),
        ),
      );

      const { getSessionProfile } = await loadAuthSession();
      mockCookieGet.mockReturnValue({ value: "valid-token" });

      const result = await getSessionProfile();

      expect(result).not.toBeNull();
      expect(result!.role).toBe("RESEARCHER");
    });
  });

  describe("getSudoCapabilities", () => {
    it("returns null when no access_token cookie exists", async () => {
      const { getSudoCapabilities } = await loadAuthSession();
      mockCookieGet.mockReturnValue(undefined);

      const result = await getSudoCapabilities();

      expect(result).toBeNull();
    });

    it("returns sudo capabilities on successful fetch", async () => {
      server.use(
        http.get(`${API_BASE}/sudo-grants/me`, () =>
          HttpResponse.json({
            hasSudo: true,
            canGrantSudo: true,
            permissions: ["CREATE_TEACHER"],
            isStaff: true,
          }),
        ),
      );

      const { getSudoCapabilities } = await loadAuthSession();
      mockCookieGet.mockReturnValue({ value: "valid-token" });

      const result = await getSudoCapabilities();

      expect(result).toEqual({
        hasSudo: true,
        canGrantSudo: true,
        permissions: ["CREATE_TEACHER"],
        isStaff: true,
      });
    });

    it("returns empty capabilities on non-ok response", async () => {
      server.use(
        http.get(`${API_BASE}/sudo-grants/me`, () =>
          HttpResponse.json({ detail: "Forbidden" }, { status: 403 }),
        ),
      );

      const { getSudoCapabilities } = await loadAuthSession();
      mockCookieGet.mockReturnValue({ value: "valid-token" });

      const result = await getSudoCapabilities();

      expect(result).toEqual({
        hasSudo: false,
        canGrantSudo: false,
        permissions: [],
        isStaff: false,
      });
    });

    it("handles missing permissions array gracefully", async () => {
      server.use(
        http.get(`${API_BASE}/sudo-grants/me`, () =>
          HttpResponse.json({
            hasSudo: true,
            canGrantSudo: false,
            permissions: "not-an-array",
            isStaff: false,
          }),
        ),
      );

      const { getSudoCapabilities } = await loadAuthSession();
      mockCookieGet.mockReturnValue({ value: "valid-token" });

      const result = await getSudoCapabilities();

      expect(result!.permissions).toEqual([]);
    });

    it("coerces falsy values to booleans", async () => {
      server.use(
        http.get(`${API_BASE}/sudo-grants/me`, () =>
          HttpResponse.json({
            hasSudo: undefined,
            canGrantSudo: null,
            permissions: [],
            isStaff: 0,
          }),
        ),
      );

      const { getSudoCapabilities } = await loadAuthSession();
      mockCookieGet.mockReturnValue({ value: "valid-token" });

      const result = await getSudoCapabilities();

      expect(result!.hasSudo).toBe(false);
      expect(result!.canGrantSudo).toBe(false);
      expect(result!.isStaff).toBe(false);
    });
  });

  describe("resolveApiBaseUrl (via SERVER_PROXY_ORIGIN)", () => {
    it("uses SERVER_PROXY_ORIGIN when localhost is configured", async () => {
      server.use(
        http.get("http://proxy:8080/api/v1/auth/me", () =>
          HttpResponse.json({
            id: "1",
            name: "Test",
            username: "test",
            email: null,
            role: "TEACHER",
            isStaff: false,
          }),
        ),
      );

      vi.resetModules();
      process.env.NEXT_PUBLIC_API_URL = API_BASE;
      process.env.SERVER_PROXY_ORIGIN = "http://proxy:8080";

      mockCookieGet = vi.fn();
      vi.doMock("next/headers", () => ({
        cookies: vi.fn(() => Promise.resolve({ get: mockCookieGet })),
      }));
      vi.doMock("react", () => ({
        cache: (fn: unknown) => fn,
      }));

      const mod = await import("@/lib/auth-session");
      mockCookieGet.mockReturnValue({ value: "valid-token" });

      const result = await mod.getSessionProfile();

      expect(result).not.toBeNull();
      expect(result!.role).toBe("TEACHER");
    });
  });
});
