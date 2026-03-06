import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockDelete = vi.fn();

function setupMocks() {
  vi.doMock("@/lib/api", () => ({
    default: { get: mockGet, post: mockPost, delete: mockDelete, patch: vi.fn() },
  }));
}

async function loadModule() {
  vi.resetModules();
  setupMocks();
  return await import("@/lib/lifecycle-api");
}

describe("lifecycle-api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("re-exports archiveCourse from course-api", async () => {
    const lifecycle = await loadModule();
    expect(typeof lifecycle.archiveCourse).toBe("function");
  });

  it("re-exports restoreCourse from course-api", async () => {
    const lifecycle = await loadModule();
    expect(typeof lifecycle.restoreCourse).toBe("function");
  });

  it("re-exports purgeCourse (deleteCourse) from course-api", async () => {
    const lifecycle = await loadModule();
    expect(typeof lifecycle.purgeCourse).toBe("function");
  });

  it("re-exports archiveAssessment from assessment-api", async () => {
    const lifecycle = await loadModule();
    expect(typeof lifecycle.archiveAssessment).toBe("function");
  });

  it("re-exports restoreAssessment from assessment-api", async () => {
    const lifecycle = await loadModule();
    expect(typeof lifecycle.restoreAssessment).toBe("function");
  });

  it("re-exports purgeAssessment (deleteAssessment) from assessment-api", async () => {
    const lifecycle = await loadModule();
    expect(typeof lifecycle.purgeAssessment).toBe("function");
  });

  it("re-exports archiveAssignment from assignment-api", async () => {
    const lifecycle = await loadModule();
    expect(typeof lifecycle.archiveAssignment).toBe("function");
  });

  it("re-exports restoreAssignment from assignment-api", async () => {
    const lifecycle = await loadModule();
    expect(typeof lifecycle.restoreAssignment).toBe("function");
  });

  it("re-exports purgeAssignment (deleteAssignment) from assignment-api", async () => {
    const lifecycle = await loadModule();
    expect(typeof lifecycle.purgeAssignment).toBe("function");
  });

  describe("archiveCourse delegates to course-api", () => {
    it("calls api.post with /courses/:id/archive", async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 1, status: "ARCHIVED" } });
      const { archiveCourse } = await loadModule();
      const result = await archiveCourse(1);
      expect(mockPost).toHaveBeenCalledWith("/courses/1/archive", {});
      expect(result.status).toBe("ARCHIVED");
    });
  });

  describe("restoreCourse delegates to course-api", () => {
    it("calls api.post with /courses/:id/restore", async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 1, status: "ACTIVE" } });
      const { restoreCourse } = await loadModule();
      const result = await restoreCourse(1);
      expect(mockPost).toHaveBeenCalledWith("/courses/1/restore", {});
      expect(result.status).toBe("ACTIVE");
    });
  });

  describe("purgeCourse delegates to course-api deleteCourse", () => {
    it("calls api.delete with /courses/:id", async () => {
      mockDelete.mockResolvedValueOnce({});
      const { purgeCourse } = await loadModule();
      await purgeCourse(1);
      expect(mockDelete).toHaveBeenCalledWith("/courses/1");
    });
  });

  describe("archiveAssessment delegates to assessment-api", () => {
    it("calls api.post with /assessments/:id/archive", async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 2, status: "ARCHIVED" } });
      const { archiveAssessment } = await loadModule();
      const result = await archiveAssessment(2);
      expect(mockPost).toHaveBeenCalledWith("/assessments/2/archive", {});
      expect(result.status).toBe("ARCHIVED");
    });
  });

  describe("restoreAssessment delegates to assessment-api", () => {
    it("calls api.post with /assessments/:id/restore", async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 2, status: "ACTIVE" } });
      const { restoreAssessment } = await loadModule();
      const result = await restoreAssessment(2);
      expect(mockPost).toHaveBeenCalledWith("/assessments/2/restore", {});
      expect(result.status).toBe("ACTIVE");
    });
  });

  describe("purgeAssessment delegates to assessment-api deleteAssessment", () => {
    it("calls api.delete with /assessments/:id", async () => {
      mockDelete.mockResolvedValueOnce({});
      const { purgeAssessment } = await loadModule();
      await purgeAssessment(2);
      expect(mockDelete).toHaveBeenCalledWith("/assessments/2");
    });
  });

  describe("archiveAssignment delegates to assignment-api", () => {
    it("calls api.post with /assignments/:id/archive", async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 3, status: "ARCHIVED" } });
      const { archiveAssignment } = await loadModule();
      const result = await archiveAssignment(3);
      expect(mockPost).toHaveBeenCalledWith("/assignments/3/archive", {});
      expect(result.status).toBe("ARCHIVED");
    });
  });

  describe("restoreAssignment delegates to assignment-api", () => {
    it("calls api.post with /assignments/:id/restore", async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 3, status: "ACTIVE" } });
      const { restoreAssignment } = await loadModule();
      const result = await restoreAssignment(3);
      expect(mockPost).toHaveBeenCalledWith("/assignments/3/restore", {});
      expect(result.status).toBe("ACTIVE");
    });
  });

  describe("purgeAssignment delegates to assignment-api deleteAssignment", () => {
    it("calls api.delete with /assignments/:id", async () => {
      mockDelete.mockResolvedValueOnce({});
      const { purgeAssignment } = await loadModule();
      await purgeAssignment(3);
      expect(mockDelete).toHaveBeenCalledWith("/assignments/3");
    });
  });
});
