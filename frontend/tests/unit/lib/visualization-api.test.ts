import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8080/api/v1";

async function loadVisualizationApi() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  return import("@/lib/visualization-api");
}

const sampleDashboard = {
  generatedAt: "2026-01-15T10:00:00Z",
  courses: [
    {
      courseId: 1,
      courseName: "Algebra",
      enrolledCount: 30,
      activeEnrollments: 28,
      assignmentCount: 5,
      avgCompletionRate: 0.85,
      avgScore: 78.5,
      pendingGrades: 3,
    },
  ],
};

const sampleCourseSummary = {
  generatedAt: "2026-01-15T10:00:00Z",
  filters: {
    startDate: null,
    endDate: null,
    category: null,
    assessmentId: null,
  },
  courseId: 1,
  courseName: "Algebra",
  enrolledCount: 30,
  assignments: [
    {
      assignmentId: 10,
      assessmentTitle: "Quiz 1",
      assessmentCategory: "MATH",
      submittedCount: 25,
      totalStudents: 30,
      completionPct: 83.3,
      gradedCount: 20,
      avgScore: 75.0,
      pendingGrades: 5,
    },
  ],
};

const sampleAssignmentSummary = {
  generatedAt: "2026-01-15T10:00:00Z",
  filters: { startDate: null, endDate: null },
  assignmentId: 10,
  assessmentTitle: "Quiz 1",
  assessmentCategory: "MATH",
  totalStudents: 30,
  submittedCount: 25,
  gradedCount: 20,
  completionPct: 83.3,
  avgScore: 75.0,
  medianScore: 78.0,
  highScore: 100.0,
  lowScore: 45.0,
  distribution: [
    { range: "0-59", count: 3 },
    { range: "60-79", count: 10 },
    { range: "80-100", count: 12 },
  ],
};

describe("visualization api", () => {
  describe("fetchDashboard", () => {
    it("fetches the teacher dashboard overview", async () => {
      server.use(
        http.get(`${API_BASE}/visualizations/dashboard`, () =>
          HttpResponse.json(sampleDashboard),
        ),
      );

      const { fetchDashboard } = await loadVisualizationApi();
      const result = await fetchDashboard();

      expect(result.generatedAt).toBe("2026-01-15T10:00:00Z");
      expect(result.courses).toHaveLength(1);
      expect(result.courses[0].courseName).toBe("Algebra");
    });

    it("propagates error on failed request", async () => {
      server.use(
        http.get(`${API_BASE}/visualizations/dashboard`, () =>
          HttpResponse.json({ detail: "Forbidden" }, { status: 403 }),
        ),
      );

      const { fetchDashboard } = await loadVisualizationApi();
      await expect(fetchDashboard()).rejects.toThrow();
    });
  });

  describe("fetchCourseSummary", () => {
    it("fetches course summary without params", async () => {
      server.use(
        http.get(`${API_BASE}/visualizations/courses/1/summary`, () =>
          HttpResponse.json(sampleCourseSummary),
        ),
      );

      const { fetchCourseSummary } = await loadVisualizationApi();
      const result = await fetchCourseSummary(1);

      expect(result.courseId).toBe(1);
      expect(result.assignments).toHaveLength(1);
    });

    it("passes optional filter params", async () => {
      server.use(
        http.get(`${API_BASE}/visualizations/courses/1/summary`, ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get("startDate")).toBe("2026-01-01");
          expect(url.searchParams.get("category")).toBe("MATH");
          return HttpResponse.json(sampleCourseSummary);
        }),
      );

      const { fetchCourseSummary } = await loadVisualizationApi();
      await fetchCourseSummary(1, {
        startDate: "2026-01-01",
        category: "MATH",
      });
    });
  });

  describe("fetchAssignmentSummary", () => {
    it("fetches assignment summary without params", async () => {
      server.use(
        http.get(`${API_BASE}/visualizations/assignments/10/summary`, () =>
          HttpResponse.json(sampleAssignmentSummary),
        ),
      );

      const { fetchAssignmentSummary } = await loadVisualizationApi();
      const result = await fetchAssignmentSummary(10);

      expect(result.assignmentId).toBe(10);
      expect(result.distribution).toHaveLength(3);
      expect(result.avgScore).toBe(75.0);
    });

    it("passes optional date filter params", async () => {
      server.use(
        http.get(`${API_BASE}/visualizations/assignments/10/summary`, ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get("startDate")).toBe("2026-01-01");
          expect(url.searchParams.get("endDate")).toBe("2026-02-01");
          return HttpResponse.json(sampleAssignmentSummary);
        }),
      );

      const { fetchAssignmentSummary } = await loadVisualizationApi();
      await fetchAssignmentSummary(10, {
        startDate: "2026-01-01",
        endDate: "2026-02-01",
      });
    });
  });
});
