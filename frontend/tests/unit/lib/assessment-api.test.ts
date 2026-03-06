import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8000/api/v1";

async function loadAssessmentApi() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  return import("@/lib/assessment-api");
}

const sampleAssessment = {
  id: 1,
  title: "Math Quiz",
  category: "MATH",
  gradingMode: "AUTO",
  scoringPolicy: "STANDARD",
  questions: [],
  questionGroups: [],
  rubricId: null,
  rubricAssessmentIds: [],
  status: "ACTIVE",
};

describe("assessment api", () => {
  describe("listAssessments", () => {
    it("returns results from paginated response", async () => {
      server.use(
        http.get(`${API_BASE}/assessments/`, () =>
          HttpResponse.json({
            count: 1,
            next: null,
            previous: null,
            results: [sampleAssessment],
          }),
        ),
      );

      const { listAssessments } = await loadAssessmentApi();
      const result = await listAssessments();

      expect(result).toHaveLength(1);
      expect(result[0].title).toBe("Math Quiz");
    });

    it("returns empty array when no assessments exist", async () => {
      server.use(
        http.get(`${API_BASE}/assessments/`, () =>
          HttpResponse.json({
            count: 0,
            next: null,
            previous: null,
            results: [],
          }),
        ),
      );

      const { listAssessments } = await loadAssessmentApi();
      const result = await listAssessments();

      expect(result).toEqual([]);
    });
  });

  describe("getAssessment", () => {
    it("fetches a single assessment by ID", async () => {
      server.use(
        http.get(`${API_BASE}/assessments/1`, () =>
          HttpResponse.json(sampleAssessment),
        ),
      );

      const { getAssessment } = await loadAssessmentApi();
      const result = await getAssessment(1);

      expect(result.id).toBe(1);
      expect(result.title).toBe("Math Quiz");
    });

    it("propagates 404 error", async () => {
      server.use(
        http.get(`${API_BASE}/assessments/999`, () =>
          HttpResponse.json({ detail: "Not found" }, { status: 404 }),
        ),
      );

      const { getAssessment } = await loadAssessmentApi();
      await expect(getAssessment(999)).rejects.toThrow();
    });
  });

  describe("createAssessment", () => {
    it("creates and returns a new assessment", async () => {
      server.use(
        http.post(`${API_BASE}/assessments/`, async ({ request }) => {
          const body = (await request.json()) as { title?: string };
          return HttpResponse.json(
            { ...sampleAssessment, id: 2, title: body.title },
            { status: 201 },
          );
        }),
      );

      const { createAssessment } = await loadAssessmentApi();
      const result = await createAssessment({
        title: "New Quiz",
        gradingMode: "MANUAL",
        questions: [],
      });

      expect(result.id).toBe(2);
      expect(result.title).toBe("New Quiz");
    });
  });

  describe("updateAssessment", () => {
    it("patches and returns the updated assessment", async () => {
      server.use(
        http.patch(`${API_BASE}/assessments/1`, async ({ request }) => {
          const body = (await request.json()) as { title?: string };
          return HttpResponse.json({ ...sampleAssessment, title: body.title });
        }),
      );

      const { updateAssessment } = await loadAssessmentApi();
      const result = await updateAssessment(1, {
        title: "Updated Quiz",
        gradingMode: "AUTO",
        questions: [],
      });

      expect(result.title).toBe("Updated Quiz");
    });
  });

  describe("deleteAssessment", () => {
    it("deletes an assessment without error", async () => {
      server.use(
        http.delete(`${API_BASE}/assessments/1`, () =>
          new HttpResponse(null, { status: 204 }),
        ),
      );

      const { deleteAssessment } = await loadAssessmentApi();
      await expect(deleteAssessment(1)).resolves.toBeUndefined();
    });

    it("propagates error on failed delete", async () => {
      server.use(
        http.delete(`${API_BASE}/assessments/1`, () =>
          HttpResponse.json({ detail: "Forbidden" }, { status: 403 }),
        ),
      );

      const { deleteAssessment } = await loadAssessmentApi();
      await expect(deleteAssessment(1)).rejects.toThrow();
    });
  });

  describe("archiveAssessment", () => {
    it("archives and returns the assessment", async () => {
      server.use(
        http.post(`${API_BASE}/assessments/1/archive`, () =>
          HttpResponse.json({ ...sampleAssessment, status: "ARCHIVED" }),
        ),
      );

      const { archiveAssessment } = await loadAssessmentApi();
      const result = await archiveAssessment(1);

      expect(result.status).toBe("ARCHIVED");
    });
  });

  describe("restoreAssessment", () => {
    it("restores and returns the assessment", async () => {
      server.use(
        http.post(`${API_BASE}/assessments/1/restore`, () =>
          HttpResponse.json({ ...sampleAssessment, status: "ACTIVE" }),
        ),
      );

      const { restoreAssessment } = await loadAssessmentApi();
      const result = await restoreAssessment(1);

      expect(result.status).toBe("ACTIVE");
    });
  });
});
