import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8080/api/v1";

async function loadSubmissionApi() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  return import("@/lib/submission-api");
}

const sampleSubmission = {
  id: 1,
  assignmentId: 10,
  studentId: 42,
  teacherId: null,
  submittedAt: "2026-01-15T10:00:00Z",
  score: 85,
  status: "SUBMITTED",
  answers: [
    { questionId: 1, type: "MULTIPLE_CHOICE", data: { selected: [0] }, score: 5 },
  ],
};

const compactSubmission = {
  id: 1,
  assignmentId: 10,
  submittedAt: "2026-01-15T10:00:00Z",
  score: 85,
  status: "SUBMITTED",
};

describe("submission api", () => {
  describe("getStudentSubmission", () => {
    it("fetches a student submission for an assignment", async () => {
      server.use(
        http.get(`${API_BASE}/students/42/assignments/10/submission/`, () =>
          HttpResponse.json(sampleSubmission),
        ),
      );

      const { getStudentSubmission } = await loadSubmissionApi();
      const result = await getStudentSubmission(42, 10);

      expect(result.id).toBe(1);
      expect(result.status).toBe("SUBMITTED");
      expect(result.answers).toHaveLength(1);
    });

    it("propagates 404 when no submission exists", async () => {
      server.use(
        http.get(`${API_BASE}/students/42/assignments/99/submission/`, () =>
          HttpResponse.json({ detail: "Not found" }, { status: 404 }),
        ),
      );

      const { getStudentSubmission } = await loadSubmissionApi();
      await expect(getStudentSubmission(42, 99)).rejects.toThrow();
    });
  });

  describe("saveDraft", () => {
    it("saves draft answers and returns the submission", async () => {
      server.use(
        http.patch(`${API_BASE}/students/42/assignments/10/draft/`, async ({ request }) => {
          const body = (await request.json()) as { answers?: unknown[] };
          return HttpResponse.json({
            ...sampleSubmission,
            status: "IN_PROGRESS",
            answers: body.answers,
          });
        }),
      );

      const { saveDraft } = await loadSubmissionApi();
      const answers = [
        { questionId: 1, type: "MULTIPLE_CHOICE" as const, data: { selected: [1] } },
      ];
      const result = await saveDraft(42, 10, answers);

      expect(result.status).toBe("IN_PROGRESS");
    });
  });

  describe("submitFinal", () => {
    it("submits final answers and transitions to SUBMITTED", async () => {
      server.use(
        http.post(`${API_BASE}/assignments/10/submissions`, async ({ request }) => {
          const body = (await request.json()) as { status?: string };
          return HttpResponse.json({
            ...sampleSubmission,
            status: body.status,
          });
        }),
      );

      const { submitFinal } = await loadSubmissionApi();
      const answers = [
        { questionId: 1, type: "MULTIPLE_CHOICE" as const, data: { selected: [0] } },
      ];
      const result = await submitFinal(10, 42, answers);

      expect(result.status).toBe("SUBMITTED");
    });
  });

  describe("getSubmission", () => {
    it("fetches a single submission by ID", async () => {
      server.use(
        http.get(`${API_BASE}/submissions/1`, () =>
          HttpResponse.json(sampleSubmission),
        ),
      );

      const { getSubmission } = await loadSubmissionApi();
      const result = await getSubmission(1);

      expect(result.id).toBe(1);
      expect(result.score).toBe(85);
    });
  });

  describe("listMySubmissions", () => {
    it("fetches submissions without status filter", async () => {
      server.use(
        http.get(`${API_BASE}/submissions/me`, ({ request }) => {
          const url = new URL(request.url);
          expect(url.search).toBe("");
          return HttpResponse.json([compactSubmission]);
        }),
      );

      const { listMySubmissions } = await loadSubmissionApi();
      const result = await listMySubmissions();

      expect(result).toHaveLength(1);
    });

    it("includes status filter in query string", async () => {
      server.use(
        http.get(`${API_BASE}/submissions/me`, ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get("status")).toBe("GRADED");
          return HttpResponse.json({
            count: 1,
            next: null,
            previous: null,
            results: [compactSubmission],
          });
        }),
      );

      const { listMySubmissions } = await loadSubmissionApi();
      await listMySubmissions("GRADED");
    });
  });

  describe("listAssignmentSubmissions", () => {
    it("fetches all submissions for an assignment", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/10/submissions`, () =>
          HttpResponse.json([compactSubmission]),
        ),
      );

      const { listAssignmentSubmissions } = await loadSubmissionApi();
      const result = await listAssignmentSubmissions(10);

      expect(result).toHaveLength(1);
    });
  });

  describe("listStudentSubmissions", () => {
    it("fetches all submissions for a student and normalizes paginated response", async () => {
      server.use(
        http.get(`${API_BASE}/students/42/submissions/`, () =>
          HttpResponse.json({
            count: 1,
            next: null,
            previous: null,
            results: [compactSubmission],
          }),
        ),
      );

      const { listStudentSubmissions } = await loadSubmissionApi();
      const result = await listStudentSubmissions(42);

      expect(result).toEqual([compactSubmission]);
    });
  });

  describe("overrideSubmissionScore", () => {
    it("sends score overrides and returns the updated submission", async () => {
      server.use(
        http.patch(`${API_BASE}/submissions/1/override-score`, async ({ request }) => {
          const body = await request.json();
          return HttpResponse.json({
            ...sampleSubmission,
            score: 90,
            status: "GRADED",
          });
        }),
      );

      const { overrideSubmissionScore } = await loadSubmissionApi();
      const result = await overrideSubmissionScore(1, [5, 4, 3]);

      expect(result.score).toBe(90);
      expect(result.status).toBe("GRADED");
    });
  });
});
