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

  it("re-exports archiveAssignmentTemplate from assignment-template-api", async () => {
    const lifecycle = await loadModule();
    expect(typeof lifecycle.archiveAssignmentTemplate).toBe("function");
  });

  it("re-exports restoreAssignmentTemplate from assignment-template-api", async () => {
    const lifecycle = await loadModule();
    expect(typeof lifecycle.restoreAssignmentTemplate).toBe("function");
  });

  it("re-exports purgeAssignmentTemplate from assignment-template-api", async () => {
    const lifecycle = await loadModule();
    expect(typeof lifecycle.purgeAssignmentTemplate).toBe("function");
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
    it("calls api.delete with /courses/:id?purge=true", async () => {
      mockDelete.mockResolvedValueOnce({});
      const { purgeCourse } = await loadModule();
      await purgeCourse(1);
      expect(mockDelete).toHaveBeenCalledWith("/courses/1?purge=true");
    });
  });

  describe("archiveAssignmentTemplate delegates to assignment-template-api", () => {
    it("calls api.post with /assignment-templates/:id/archive", async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 2, status: "ARCHIVED" } });
      const { archiveAssignmentTemplate } = await loadModule();
      const result = await archiveAssignmentTemplate(2);
      expect(mockPost).toHaveBeenCalledWith("/assignment-templates/2/archive", {});
      expect(result.status).toBe("ARCHIVED");
    });
  });

  describe("restoreAssignmentTemplate delegates to assignment-template-api", () => {
    it("calls api.post with /assignment-templates/:id/restore", async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 2, status: "ACTIVE" } });
      const { restoreAssignmentTemplate } = await loadModule();
      const result = await restoreAssignmentTemplate(2);
      expect(mockPost).toHaveBeenCalledWith("/assignment-templates/2/restore", {});
      expect(result.status).toBe("ACTIVE");
    });
  });

  describe("purgeAssignmentTemplate delegates to assignment-template-api", () => {
    it("calls api.delete with /assignment-templates/:id?purge=true", async () => {
      mockDelete.mockResolvedValueOnce({});
      const { purgeAssignmentTemplate } = await loadModule();
      await purgeAssignmentTemplate(2);
      expect(mockDelete).toHaveBeenCalledWith("/assignment-templates/2?purge=true");
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
    it("calls api.delete with /assignments/:id?purge=true", async () => {
      mockDelete.mockResolvedValueOnce({});
      const { purgeAssignment } = await loadModule();
      await purgeAssignment(3);
      expect(mockDelete).toHaveBeenCalledWith("/assignments/3?purge=true");
    });
  });
});
