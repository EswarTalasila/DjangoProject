import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

function setupModuleMocks() {
  vi.doMock("@/lib/api", () => ({
    default: { get: mockGet, post: mockPost, patch: mockPatch, delete: mockDelete },
  }));
}

async function loadModule() {
  vi.resetModules();
  setupModuleMocks();
  return import("@/lib/course-api");
}

describe("course-api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("listCourses", () => {
    it("returns results from paginated response", async () => {
      mockGet.mockResolvedValueOnce({
        data: {
          count: 1,
          next: null,
          previous: null,
          results: [{ id: 10, name: "Algebra", studentCount: 3, assignmentIds: [1] }],
        },
      });
      const { listCourses } = await loadModule();
      const courses = await listCourses();
      expect(mockGet).toHaveBeenCalledWith("/courses/", { params: undefined });
      expect(courses).toEqual([{ id: 10, name: "Algebra", studentCount: 3, assignmentIds: [1] }]);
    });

    it("returns raw array response", async () => {
      mockGet.mockResolvedValueOnce({
        data: [{ id: 5, name: "Bio" }],
      });
      const { listCourses } = await loadModule();
      const courses = await listCourses();
      expect(courses).toEqual([{ id: 5, name: "Bio" }]);
    });

    it("passes includeArchived param when true", async () => {
      mockGet.mockResolvedValueOnce({ data: [] });
      const { listCourses } = await loadModule();
      await listCourses({ includeArchived: true });
      expect(mockGet).toHaveBeenCalledWith("/courses/", { params: { includeArchived: true } });
    });
  });

  describe("createCourse", () => {
    it("posts to /courses/ with name", async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 11, name: "New Course" } });
      const { createCourse } = await loadModule();
      const result = await createCourse("New Course");
      expect(mockPost).toHaveBeenCalledWith("/courses/", { name: "New Course" });
      expect(result).toEqual({ id: 11, name: "New Course" });
    });
  });

  describe("getCourse", () => {
    it("fetches a single course by ID", async () => {
      mockGet.mockResolvedValueOnce({ data: { id: 7, name: "History" } });
      const { getCourse } = await loadModule();
      const result = await getCourse(7);
      expect(mockGet).toHaveBeenCalledWith("/courses/7");
      expect(result).toEqual({ id: 7, name: "History" });
    });
  });

  describe("updateCourse", () => {
    it("patches a course with new name", async () => {
      mockPatch.mockResolvedValueOnce({ data: { id: 7, name: "Updated" } });
      const { updateCourse } = await loadModule();
      const result = await updateCourse(7, "Updated");
      expect(mockPatch).toHaveBeenCalledWith("/courses/7", { name: "Updated" });
      expect(result).toEqual({ id: 7, name: "Updated" });
    });
  });

  describe("deleteCourse", () => {
    it("deletes a course by ID", async () => {
      mockDelete.mockResolvedValueOnce({});
      const { deleteCourse } = await loadModule();
      await deleteCourse(7);
      expect(mockDelete).toHaveBeenCalledWith("/courses/7");
    });
  });

  describe("listStudentsInCourse", () => {
    it("returns results from paginated response", async () => {
      mockGet.mockResolvedValueOnce({
        data: {
          count: 1,
          next: null,
          previous: null,
          results: [{ id: 1, name: "Alice", username: "alice", role: "STUDENT", consent: true, courseId: 5, enrolledAt: null }],
        },
      });
      const { listStudentsInCourse } = await loadModule();
      const students = await listStudentsInCourse(5);
      expect(mockGet).toHaveBeenCalledWith("/courses/5/students");
      expect(students).toHaveLength(1);
      expect(students[0].name).toBe("Alice");
    });

    it("returns raw array response", async () => {
      mockGet.mockResolvedValueOnce({
        data: [{ id: 2, name: "Bob" }],
      });
      const { listStudentsInCourse } = await loadModule();
      const students = await listStudentsInCourse(5);
      expect(students).toEqual([{ id: 2, name: "Bob" }]);
    });
  });

  describe("addStudentToCourse", () => {
    it("posts student payload to course students endpoint", async () => {
      const student = { id: 3, name: "Charlie", username: "charlie", role: "STUDENT", consent: false, courseId: 5, enrolledAt: null };
      mockPost.mockResolvedValueOnce({ data: student });
      const { addStudentToCourse } = await loadModule();
      const result = await addStudentToCourse(5, { name: "Charlie", consent: false });
      expect(mockPost).toHaveBeenCalledWith("/courses/5/students", { name: "Charlie", consent: false });
      expect(result).toEqual(student);
    });
  });

  describe("removeStudentFromCourse", () => {
    it("deletes student from course", async () => {
      mockDelete.mockResolvedValueOnce({});
      const { removeStudentFromCourse } = await loadModule();
      await removeStudentFromCourse(5, 3);
      expect(mockDelete).toHaveBeenCalledWith("/courses/5/students/3");
    });
  });

  describe("archiveCourse", () => {
    it("posts to archive endpoint", async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 5, name: "Archived", status: "ARCHIVED" } });
      const { archiveCourse } = await loadModule();
      const result = await archiveCourse(5);
      expect(mockPost).toHaveBeenCalledWith("/courses/5/archive", {});
      expect(result.status).toBe("ARCHIVED");
    });
  });

  describe("restoreCourse", () => {
    it("posts to restore endpoint", async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 5, name: "Restored", status: "ACTIVE" } });
      const { restoreCourse } = await loadModule();
      const result = await restoreCourse(5);
      expect(mockPost).toHaveBeenCalledWith("/courses/5/restore", {});
      expect(result.status).toBe("ACTIVE");
    });
  });
});
