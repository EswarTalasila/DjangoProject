import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8080/api/v1";

async function loadAssignmentTemplateApi() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  return import("@/lib/assignment-template-api");
}

const sampleAssignmentTemplate = {
  id: 1,
  title: "Math Quiz",
  category: "MATH",
  gradingMode: "AUTO",
  scoringPolicy: "STANDARD",
  questions: [],
  questionGroups: [],
  rubricId: null,
  rubricAssignmentTemplateIds: [],
  status: "ACTIVE",
};

describe("assignment_template api", () => {
  describe("listAssignmentTemplates", () => {
    it("returns results from paginated response", async () => {
      server.use(
        http.get(`${API_BASE}/assignment-templates/`, () =>
          HttpResponse.json({
            count: 1,
            next: null,
            previous: null,
            results: [sampleAssignmentTemplate],
          }),
        ),
      );

      const { listAssignmentTemplates } = await loadAssignmentTemplateApi();
      const result = await listAssignmentTemplates();

      expect(result).toHaveLength(1);
      expect(result[0].title).toBe("Math Quiz");
    });

    it("returns empty array when no assignment_templates exist", async () => {
      server.use(
        http.get(`${API_BASE}/assignment-templates/`, () =>
          HttpResponse.json({
            count: 0,
            next: null,
            previous: null,
            results: [],
          }),
        ),
      );

      const { listAssignmentTemplates } = await loadAssignmentTemplateApi();
      const result = await listAssignmentTemplates();

      expect(result).toEqual([]);
    });
  });

  describe("getAssignmentTemplate", () => {
    it("fetches a single assignment_template by ID", async () => {
      server.use(
        http.get(`${API_BASE}/assignment-templates/1`, () =>
          HttpResponse.json(sampleAssignmentTemplate),
        ),
      );

      const { getAssignmentTemplate } = await loadAssignmentTemplateApi();
      const result = await getAssignmentTemplate(1);

      expect(result.id).toBe(1);
      expect(result.title).toBe("Math Quiz");
    });

    it("propagates 404 error", async () => {
      server.use(
        http.get(`${API_BASE}/assignment-templates/999`, () =>
          HttpResponse.json({ detail: "Not found" }, { status: 404 }),
        ),
      );

      const { getAssignmentTemplate } = await loadAssignmentTemplateApi();
      await expect(getAssignmentTemplate(999)).rejects.toThrow();
    });
  });

  describe("createAssignmentTemplate", () => {
    it("creates and returns a new assignment_template", async () => {
      server.use(
        http.post(`${API_BASE}/assignment-templates/`, async ({ request }) => {
          const body = (await request.json()) as { title?: string };
          return HttpResponse.json(
            { ...sampleAssignmentTemplate, id: 2, title: body.title },
            { status: 201 },
          );
        }),
      );

      const { createAssignmentTemplate } = await loadAssignmentTemplateApi();
      const result = await createAssignmentTemplate({
        title: "New Quiz",
        gradingMode: "MANUAL",
        questions: [],
      });

      expect(result.id).toBe(2);
      expect(result.title).toBe("New Quiz");
    });
  });

  describe("updateAssignmentTemplate", () => {
    it("patches and returns the updated assignment_template", async () => {
      server.use(
        http.patch(`${API_BASE}/assignment-templates/1`, async ({ request }) => {
          const body = (await request.json()) as { title?: string };
          return HttpResponse.json({ ...sampleAssignmentTemplate, title: body.title });
        }),
      );

      const { updateAssignmentTemplate } = await loadAssignmentTemplateApi();
      const result = await updateAssignmentTemplate(1, {
        title: "Updated Quiz",
        gradingMode: "AUTO",
        questions: [],
      });

      expect(result.title).toBe("Updated Quiz");
    });
  });

  describe("deleteAssignmentTemplate", () => {
    it("deletes an assignment_template without error", async () => {
      server.use(
        http.delete(`${API_BASE}/assignment-templates/1`, () =>
          new HttpResponse(null, { status: 204 }),
        ),
      );

      const { deleteAssignmentTemplate } = await loadAssignmentTemplateApi();
      await expect(deleteAssignmentTemplate(1)).resolves.toBeUndefined();
    });

    it("propagates error on failed delete", async () => {
      server.use(
        http.delete(`${API_BASE}/assignment-templates/1`, () =>
          HttpResponse.json({ detail: "Forbidden" }, { status: 403 }),
        ),
      );

      const { deleteAssignmentTemplate } = await loadAssignmentTemplateApi();
      await expect(deleteAssignmentTemplate(1)).rejects.toThrow();
    });
  });

  describe("archiveAssignmentTemplate", () => {
    it("archives and returns the assignment_template", async () => {
      server.use(
        http.post(`${API_BASE}/assignment-templates/1/archive`, () =>
          HttpResponse.json({ ...sampleAssignmentTemplate, status: "ARCHIVED" }),
        ),
      );

      const { archiveAssignmentTemplate } = await loadAssignmentTemplateApi();
      const result = await archiveAssignmentTemplate(1);

      expect(result.status).toBe("ARCHIVED");
    });
  });

  describe("restoreAssignmentTemplate", () => {
    it("restores and returns the assignment_template", async () => {
      server.use(
        http.post(`${API_BASE}/assignment-templates/1/restore`, () =>
          HttpResponse.json({ ...sampleAssignmentTemplate, status: "ACTIVE" }),
        ),
      );

      const { restoreAssignmentTemplate } = await loadAssignmentTemplateApi();
      const result = await restoreAssignmentTemplate(1);

      expect(result.status).toBe("ACTIVE");
    });
  });
});
