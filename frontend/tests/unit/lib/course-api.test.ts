import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8000/api/v1";

async function loadCourseApi() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  return import("@/lib/course-api");
}

describe("course api", () => {
  it("reads paginated course list responses", async () => {
    server.use(
      http.get(`${API_BASE}/courses/`, () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [{ id: 10, name: "Algebra", studentCount: 3, assignmentIds: [1, 2] }],
        }),
      ),
    );

    const { listCourses } = await loadCourseApi();
    const courses = await listCourses();

    expect(courses).toEqual([{ id: 10, name: "Algebra", studentCount: 3, assignmentIds: [1, 2] }]);
  });

  it("creates a course by name", async () => {
    server.use(
      http.post(`${API_BASE}/courses/`, async ({ request }) => {
        const body = (await request.json()) as { name?: string };
        if (body.name !== "New Course") {
          return HttpResponse.json({ detail: "bad payload" }, { status: 400 });
        }
        return HttpResponse.json(
          { id: 11, name: "New Course", studentCount: 0, assignmentIds: [] },
          { status: 201 },
        );
      }),
    );

    const { createCourse } = await loadCourseApi();
    const created = await createCourse("New Course");

    expect(created.id).toBe(11);
    expect(created.name).toBe("New Course");
  });
});
