import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8000/api/v1";

async function loadRegistrationCodeApi() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  return import("@/lib/registration-code-api");
}

describe("registration code api", () => {
  it("returns created student invite code", async () => {
    server.use(
      http.post(`${API_BASE}/codes`, async ({ request }) => {
        const body = (await request.json()) as { codeType?: string; courseId?: number };
        if (body.codeType !== "STUDENT" || body.courseId !== 42) {
          return HttpResponse.json({ detail: "bad payload" }, { status: 400 });
        }
        return HttpResponse.json(
          {
            count: 1,
            codes: [{ code: "REG-ABC-123" }],
          },
          { status: 201 },
        );
      }),
    );

    const { createStudentRegistrationCode } = await loadRegistrationCodeApi();
    const code = await createStudentRegistrationCode(42);

    expect(code).toBe("REG-ABC-123");
  });

  it("throws when backend does not return plaintext code", async () => {
    server.use(
      http.post(`${API_BASE}/codes`, () =>
        HttpResponse.json(
          {
            count: 1,
            codes: [{ code: null }],
          },
          { status: 201 },
        ),
      ),
    );

    const { createStudentRegistrationCode } = await loadRegistrationCodeApi();
    await expect(createStudentRegistrationCode(42)).rejects.toThrow(
      "Registration code was not returned by the server.",
    );
  });
});
