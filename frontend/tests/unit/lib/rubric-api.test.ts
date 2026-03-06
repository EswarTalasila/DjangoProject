import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8000/api/v1";

async function loadRubricApi() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  return import("@/lib/rubric-api");
}

const sampleRubric = {
  id: 1,
  title: "Writing Rubric",
  description: "Evaluates essay quality",
  status: "ACTIVE",
  createdBy: 10,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
  criteria: [
    {
      id: 1,
      title: "Grammar",
      description: "Proper grammar usage",
      orderIndex: 0,
      weight: 1,
      levels: [
        { id: 1, label: "Excellent", points: 5, description: "No errors", orderIndex: 0 },
        { id: 2, label: "Poor", points: 1, description: "Many errors", orderIndex: 1 },
      ],
    },
  ],
};

describe("rubric api", () => {
  describe("listRubrics", () => {
    it("returns results from paginated response", async () => {
      server.use(
        http.get(`${API_BASE}/rubrics/`, () =>
          HttpResponse.json({
            count: 1,
            next: null,
            previous: null,
            results: [sampleRubric],
          }),
        ),
      );

      const { listRubrics } = await loadRubricApi();
      const result = await listRubrics();

      expect(result).toHaveLength(1);
      expect(result[0].title).toBe("Writing Rubric");
    });

    it("returns empty array when no rubrics exist", async () => {
      server.use(
        http.get(`${API_BASE}/rubrics/`, () =>
          HttpResponse.json({
            count: 0,
            next: null,
            previous: null,
            results: [],
          }),
        ),
      );

      const { listRubrics } = await loadRubricApi();
      const result = await listRubrics();

      expect(result).toEqual([]);
    });
  });

  describe("getRubric", () => {
    it("fetches a single rubric by ID", async () => {
      server.use(
        http.get(`${API_BASE}/rubrics/1`, () =>
          HttpResponse.json(sampleRubric),
        ),
      );

      const { getRubric } = await loadRubricApi();
      const result = await getRubric(1);

      expect(result.id).toBe(1);
      expect(result.criteria).toHaveLength(1);
      expect(result.criteria[0].levels).toHaveLength(2);
    });

    it("propagates 404 error", async () => {
      server.use(
        http.get(`${API_BASE}/rubrics/999`, () =>
          HttpResponse.json({ detail: "Not found" }, { status: 404 }),
        ),
      );

      const { getRubric } = await loadRubricApi();
      await expect(getRubric(999)).rejects.toThrow();
    });
  });

  describe("createRubric", () => {
    it("creates and returns a new rubric", async () => {
      server.use(
        http.post(`${API_BASE}/rubrics/`, async ({ request }) => {
          const body = (await request.json()) as { title?: string };
          return HttpResponse.json(
            { ...sampleRubric, id: 2, title: body.title },
            { status: 201 },
          );
        }),
      );

      const { createRubric } = await loadRubricApi();
      const result = await createRubric({ title: "New Rubric" });

      expect(result.id).toBe(2);
      expect(result.title).toBe("New Rubric");
    });
  });

  describe("updateRubric", () => {
    it("patches and returns the updated rubric", async () => {
      server.use(
        http.patch(`${API_BASE}/rubrics/1`, async ({ request }) => {
          const body = (await request.json()) as { title?: string };
          return HttpResponse.json({ ...sampleRubric, title: body.title });
        }),
      );

      const { updateRubric } = await loadRubricApi();
      const result = await updateRubric(1, { title: "Updated Rubric" });

      expect(result.title).toBe("Updated Rubric");
    });
  });

  describe("deleteRubric", () => {
    it("deletes a rubric without error", async () => {
      server.use(
        http.delete(`${API_BASE}/rubrics/1`, () =>
          new HttpResponse(null, { status: 204 }),
        ),
      );

      const { deleteRubric } = await loadRubricApi();
      await expect(deleteRubric(1)).resolves.toBeUndefined();
    });

    it("propagates error on failed delete", async () => {
      server.use(
        http.delete(`${API_BASE}/rubrics/1`, () =>
          HttpResponse.json({ detail: "Forbidden" }, { status: 403 }),
        ),
      );

      const { deleteRubric } = await loadRubricApi();
      await expect(deleteRubric(1)).rejects.toThrow();
    });
  });

  describe("archiveRubric", () => {
    it("archives and returns the rubric", async () => {
      server.use(
        http.post(`${API_BASE}/rubrics/1/archive`, () =>
          HttpResponse.json({ ...sampleRubric, status: "ARCHIVED" }),
        ),
      );

      const { archiveRubric } = await loadRubricApi();
      const result = await archiveRubric(1);

      expect(result.status).toBe("ARCHIVED");
    });
  });
});
