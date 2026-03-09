import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8000/api/v1";

async function loadSudoApi() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  return import("@/lib/sudo-api");
}

describe("sudo api", () => {
  it("lists sudo grants", async () => {
    server.use(
      http.get(`${API_BASE}/sudo-grants`, () =>
        HttpResponse.json([
          {
            id: 1,
            user: { id: 10, username: "researcher1", name: "Researcher One" },
            permissions: ["CREATE_TEACHER"],
            canGrantSudo: false,
            grantedAt: "2026-01-15T10:00:00Z",
          },
        ]),
      ),
    );

    const { listSudoGrants } = await loadSudoApi();
    const grants = await listSudoGrants();

    expect(grants).toHaveLength(1);
    expect(grants[0].user.username).toBe("researcher1");
    expect(grants[0].permissions).toEqual(["CREATE_TEACHER"]);
  });

  it("grants sudo to a researcher", async () => {
    server.use(
      http.post(`${API_BASE}/sudo-grants`, async ({ request }) => {
        const body = (await request.json()) as {
          user_id?: number;
          permissions?: string[];
        };
        if (body.user_id !== 10) {
          return HttpResponse.json({ detail: "bad payload" }, { status: 400 });
        }
        return HttpResponse.json(
          { message: "Sudo granted", grant_id: 5 },
          { status: 201 },
        );
      }),
    );

    const { grantSudo } = await loadSudoApi();
    const result = await grantSudo({
      user_id: 10,
      permissions: ["CREATE_TEACHER"],
    });

    expect(result.message).toBe("Sudo granted");
    expect(result.grant_id).toBe(5);
  });

  it("revokes a sudo grant", async () => {
    server.use(
      http.delete(`${API_BASE}/sudo-grants/5`, () =>
        new HttpResponse(null, { status: 204 }),
      ),
    );

    const { revokeSudoGrant } = await loadSudoApi();
    await expect(revokeSudoGrant(5)).resolves.toBeUndefined();
  });

  it("propagates error on failed grant", async () => {
    server.use(
      http.post(`${API_BASE}/sudo-grants`, () =>
        HttpResponse.json({ detail: "Forbidden" }, { status: 403 }),
      ),
    );

    const { grantSudo } = await loadSudoApi();
    await expect(
      grantSudo({ user_id: 10, permissions: ["CREATE_TEACHER"] }),
    ).rejects.toThrow();
  });
});
