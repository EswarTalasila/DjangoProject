import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8080/api/v1";

async function loadAssignmentApi() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  return import("@/lib/assignment-api");
}

const sampleAssignment = {
  id: 1,
  title: "HW 1",
  assignmentTemplateId: 10,
  assignmentTemplateTitle: "Math Quiz",
  audienceType: "COURSE",
  courseId: 5,
  targetTeacherId: null,
  openAt: "2026-01-01T00:00:00Z",
  dueAt: "2026-02-01T00:00:00Z",
  status: "ACTIVE",
};

describe("assignment api", () => {
  describe("createAssignment", () => {
    it("creates and returns a new assignment", async () => {
      server.use(
        http.post(`${API_BASE}/assignments/`, async ({ request }) => {
          const body = (await request.json()) as { assignmentTemplateId?: number };
          return HttpResponse.json(
            { ...sampleAssignment, assignmentTemplateId: body.assignmentTemplateId },
            { status: 201 },
          );
        }),
      );

      const { createAssignment } = await loadAssignmentApi();
      const result = await createAssignment({
        assignmentTemplateId: 10,
        audienceType: "COURSE",
        courseId: 5,
        openAt: "2026-01-01T00:00:00Z",
      });

      expect(result.id).toBe(1);
      expect(result.assignmentTemplateId).toBe(10);
    });
  });

  describe("getAssignment", () => {
    it("fetches a single assignment by ID", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/1`, () =>
          HttpResponse.json(sampleAssignment),
        ),
      );

      const { getAssignment } = await loadAssignmentApi();
      const result = await getAssignment(1);

      expect(result.id).toBe(1);
      expect(result.title).toBe("HW 1");
    });

    it("propagates 404 error", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/999`, () =>
          HttpResponse.json({ detail: "Not found" }, { status: 404 }),
        ),
      );

      const { getAssignment } = await loadAssignmentApi();
      await expect(getAssignment(999)).rejects.toThrow();
    });
  });

  describe("updateAssignment", () => {
    it("patches and returns the updated assignment", async () => {
      server.use(
        http.patch(`${API_BASE}/assignments/1`, async ({ request }) => {
          const body = (await request.json()) as { title?: string };
          return HttpResponse.json({ ...sampleAssignment, title: body.title });
        }),
      );

      const { updateAssignment } = await loadAssignmentApi();
      const result = await updateAssignment(1, { title: "HW 1 Updated" });

      expect(result.title).toBe("HW 1 Updated");
    });
  });

  describe("purgeAssignment", () => {
    it("purges an archived assignment without error", async () => {
      server.use(
        http.delete(`${API_BASE}/assignments/1`, ({ request }) => {
          expect(new URL(request.url).searchParams.get("purge")).toBe("true");
          return new HttpResponse(null, { status: 204 });
        }),
      );

      const { purgeAssignment } = await loadAssignmentApi();
      await expect(purgeAssignment(1)).resolves.toBeUndefined();
    });
  });

  describe("archiveAssignment", () => {
    it("archives and returns the assignment", async () => {
      server.use(
        http.post(`${API_BASE}/assignments/1/archive`, () =>
          HttpResponse.json({ ...sampleAssignment, status: "ARCHIVED" }),
        ),
      );

      const { archiveAssignment } = await loadAssignmentApi();
      const result = await archiveAssignment(1);

      expect(result.status).toBe("ARCHIVED");
    });
  });

  describe("restoreAssignment", () => {
    it("restores and returns the assignment", async () => {
      server.use(
        http.post(`${API_BASE}/assignments/1/restore`, () =>
          HttpResponse.json({ ...sampleAssignment, status: "ACTIVE" }),
        ),
      );

      const { restoreAssignment } = await loadAssignmentApi();
      const result = await restoreAssignment(1);

      expect(result.status).toBe("ACTIVE");
    });
  });

  describe("archive bundle helpers", () => {
    it("fetches archive bundle metadata", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/1/archive-bundle`, () =>
          HttpResponse.json({
            id: 7,
            assignmentId: 1,
            identifiable: true,
            filename: "bundle.zip",
            sizeBytes: 1234,
            sha256Hash: "abc",
            generatedAt: "2026-01-01T00:00:00Z",
            generatedByUserId: 3,
            manifest: {},
          }),
        ),
      );

      const { getAssignmentArchiveBundle } = await loadAssignmentApi();
      const result = await getAssignmentArchiveBundle(1);

      expect(result.filename).toBe("bundle.zip");
      expect(result.assignmentId).toBe(1);
    });

    it("generates archive bundle metadata", async () => {
      server.use(
        http.post(`${API_BASE}/assignments/1/archive-bundle`, () =>
          HttpResponse.json(
            {
              id: 7,
              assignmentId: 1,
              identifiable: true,
              filename: "bundle.zip",
              sizeBytes: 1234,
              sha256Hash: "abc",
              generatedAt: "2026-01-01T00:00:00Z",
              generatedByUserId: 3,
              manifest: {},
            },
            { status: 201 },
          ),
        ),
      );

      const { generateAssignmentArchiveBundle } = await loadAssignmentApi();
      const result = await generateAssignmentArchiveBundle(1);

      expect(result.filename).toBe("bundle.zip");
    });

    it("downloads archive bundle zip data", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/1/archive-bundle/download`, () =>
          new HttpResponse(new Blob(["zipdata"]), {
            status: 200,
            headers: { "content-disposition": 'attachment; filename="archive.zip"' },
          }),
        ),
      );

      const { downloadAssignmentArchiveBundle } = await loadAssignmentApi();
      const result = await downloadAssignmentArchiveBundle(1);

      expect(result.filename).toBe("archive.zip");
      expect(result.blob).toBeInstanceOf(Blob);
    });
  });

  describe("listAssignmentsByCourse", () => {
    it("handles paginated response", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/courses/5`, () =>
          HttpResponse.json({
            count: 1,
            next: null,
            previous: null,
            results: [sampleAssignment],
          }),
        ),
      );

      const { listAssignmentsByCourse } = await loadAssignmentApi();
      const result = await listAssignmentsByCourse(5);

      expect(result).toHaveLength(1);
      expect(result[0].courseId).toBe(5);
    });

    it("handles flat array response", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/courses/5`, () =>
          HttpResponse.json([sampleAssignment]),
        ),
      );

      const { listAssignmentsByCourse } = await loadAssignmentApi();
      const result = await listAssignmentsByCourse(5);

      expect(result).toHaveLength(1);
    });

    it("passes includeArchived=true when requested", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/courses/5`, ({ request }) => {
          expect(new URL(request.url).searchParams.get("includeArchived")).toBe("true");
          return HttpResponse.json({
            count: 1,
            next: null,
            previous: null,
            results: [sampleAssignment],
          });
        }),
      );

      const { listAssignmentsByCourse } = await loadAssignmentApi();
      const result = await listAssignmentsByCourse(5, { includeArchived: true });

      expect(result).toHaveLength(1);
    });
  });

  describe("listAssignmentsForUser", () => {
    it("handles paginated response with numeric user ID", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/users/42`, () =>
          HttpResponse.json({
            count: 1,
            next: null,
            previous: null,
            results: [sampleAssignment],
          }),
        ),
      );

      const { listAssignmentsForUser } = await loadAssignmentApi();
      const result = await listAssignmentsForUser(42);

      expect(result).toHaveLength(1);
    });

    it("handles flat array response with string user ID", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/users/me`, () =>
          HttpResponse.json([sampleAssignment]),
        ),
      );

      const { listAssignmentsForUser } = await loadAssignmentApi();
      const result = await listAssignmentsForUser("me");

      expect(result).toHaveLength(1);
    });
  });
});
