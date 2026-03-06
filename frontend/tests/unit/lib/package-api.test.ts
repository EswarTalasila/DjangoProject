import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost:8000/api/v1";

async function loadPackageApi() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  return import("@/lib/package-api");
}

const sampleNode = {
  id: 1,
  parentId: null,
  nodeType: "FILE",
  label: "roster.csv",
  orderIndex: 0,
  datasetBinding: "ROSTER",
  bindingCourseId: 5,
  filters: null,
  identifiable: false,
  includeAnswers: false,
  sourceType: "LIVE",
  snapshotId: null,
};

const sampleWorkspace = {
  id: 1,
  name: "Export Package",
  description: "Test package",
  status: "DRAFT",
  scopeCourseId: null,
  revision: 1,
  createdBy: 10,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
  nodes: [sampleNode],
};

const sampleBuildJob = {
  id: 1,
  workspaceId: 1,
  status: "COMPLETED",
  strictMode: false,
  mode: "live",
  snapshotId: null,
  createdBy: 10,
  createdAt: "2026-01-01T00:00:00Z",
  artifactId: 100,
};

const sampleSnapshot = {
  id: 1,
  workspaceId: 1,
  datasetBinding: "ROSTER",
  scopeCourseId: null,
  filters: null,
  includeAnswers: false,
  identifiable: false,
  rowCount: 50,
  fileSize: 1024,
  checksumSha256: "abc123",
  status: "READY",
  errorMessage: "",
  metadata: {},
  expiresAt: null,
  createdAt: "2026-01-01T00:00:00Z",
  createdBy: 10,
};

describe("package api", () => {
  describe("listWorkspaces", () => {
    it("returns all workspaces", async () => {
      server.use(
        http.get(`${API_BASE}/packages/workspaces`, () =>
          HttpResponse.json([sampleWorkspace]),
        ),
      );

      const { listWorkspaces } = await loadPackageApi();
      const result = await listWorkspaces();

      expect(result).toHaveLength(1);
      expect(result[0].name).toBe("Export Package");
    });
  });

  describe("createWorkspace", () => {
    it("creates and returns a new workspace", async () => {
      server.use(
        http.post(`${API_BASE}/packages/workspaces`, async ({ request }) => {
          const body = (await request.json()) as { name?: string };
          return HttpResponse.json(
            { ...sampleWorkspace, id: 2, name: body.name, nodes: [] },
            { status: 201 },
          );
        }),
      );

      const { createWorkspace } = await loadPackageApi();
      const result = await createWorkspace({ name: "New Package" });

      expect(result.id).toBe(2);
      expect(result.name).toBe("New Package");
    });
  });

  describe("getWorkspace", () => {
    it("fetches a single workspace with nodes", async () => {
      server.use(
        http.get(`${API_BASE}/packages/workspaces/1`, () =>
          HttpResponse.json(sampleWorkspace),
        ),
      );

      const { getWorkspace } = await loadPackageApi();
      const result = await getWorkspace(1);

      expect(result.id).toBe(1);
      expect(result.nodes).toHaveLength(1);
    });
  });

  describe("updateWorkspace", () => {
    it("patches and returns the updated workspace", async () => {
      server.use(
        http.patch(`${API_BASE}/packages/workspaces/1`, async ({ request }) => {
          const body = (await request.json()) as { name?: string };
          return HttpResponse.json({ ...sampleWorkspace, name: body.name });
        }),
      );

      const { updateWorkspace } = await loadPackageApi();
      const result = await updateWorkspace(1, { name: "Renamed Package" });

      expect(result.name).toBe("Renamed Package");
    });
  });

  describe("deleteWorkspace", () => {
    it("deletes a workspace without error", async () => {
      server.use(
        http.delete(`${API_BASE}/packages/workspaces/1`, () =>
          new HttpResponse(null, { status: 204 }),
        ),
      );

      const { deleteWorkspace } = await loadPackageApi();
      await expect(deleteWorkspace(1)).resolves.toBeUndefined();
    });
  });

  describe("addNode", () => {
    it("adds a node to a workspace", async () => {
      server.use(
        http.post(`${API_BASE}/packages/workspaces/1/nodes`, async ({ request }) => {
          const body = (await request.json()) as { label?: string };
          return HttpResponse.json(
            { ...sampleNode, id: 2, label: body.label },
            { status: 201 },
          );
        }),
      );

      const { addNode } = await loadPackageApi();
      const result = await addNode(1, { nodeType: "FILE", label: "data.csv" });

      expect(result.id).toBe(2);
      expect(result.label).toBe("data.csv");
    });
  });

  describe("updateNode", () => {
    it("patches and returns the updated node", async () => {
      server.use(
        http.patch(`${API_BASE}/packages/workspaces/1/nodes/1`, async ({ request }) => {
          const body = (await request.json()) as { label?: string };
          return HttpResponse.json({ ...sampleNode, label: body.label });
        }),
      );

      const { updateNode } = await loadPackageApi();
      const result = await updateNode(1, 1, { label: "renamed.csv" });

      expect(result.label).toBe("renamed.csv");
    });
  });

  describe("deleteNode", () => {
    it("deletes a node without error", async () => {
      server.use(
        http.delete(`${API_BASE}/packages/workspaces/1/nodes/1`, () =>
          new HttpResponse(null, { status: 204 }),
        ),
      );

      const { deleteNode } = await loadPackageApi();
      await expect(deleteNode(1, 1)).resolves.toBeUndefined();
    });
  });

  describe("validateWorkspace", () => {
    it("validates a workspace and returns results", async () => {
      const validationResult = {
        valid: true,
        violations: [],
        warnings: [],
        fileCount: 2,
        estimatedRows: 100,
      };

      server.use(
        http.post(`${API_BASE}/packages/workspaces/1/validate`, () =>
          HttpResponse.json(validationResult),
        ),
      );

      const { validateWorkspace } = await loadPackageApi();
      const result = await validateWorkspace(1);

      expect(result.valid).toBe(true);
      expect(result.fileCount).toBe(2);
    });

    it("accepts optional payload", async () => {
      server.use(
        http.post(`${API_BASE}/packages/workspaces/1/validate`, async ({ request }) => {
          const body = (await request.json()) as { strictMode?: boolean };
          return HttpResponse.json({
            valid: false,
            violations: [{ nodeId: 1, code: "MISSING_BINDING", message: "No binding" }],
            warnings: [],
            fileCount: 0,
            estimatedRows: 0,
          });
        }),
      );

      const { validateWorkspace } = await loadPackageApi();
      const result = await validateWorkspace(1, { strictMode: true });

      expect(result.valid).toBe(false);
      expect(result.violations).toHaveLength(1);
    });
  });

  describe("buildWorkspace", () => {
    it("starts a build job", async () => {
      server.use(
        http.post(`${API_BASE}/packages/workspaces/1/build`, () =>
          HttpResponse.json(sampleBuildJob, { status: 201 }),
        ),
      );

      const { buildWorkspace } = await loadPackageApi();
      const result = await buildWorkspace(1);

      expect(result.id).toBe(1);
      expect(result.status).toBe("COMPLETED");
    });

    it("accepts optional build payload", async () => {
      server.use(
        http.post(`${API_BASE}/packages/workspaces/1/build`, () =>
          HttpResponse.json({ ...sampleBuildJob, strictMode: true }),
        ),
      );

      const { buildWorkspace } = await loadPackageApi();
      const result = await buildWorkspace(1, { strictMode: true });

      expect(result.strictMode).toBe(true);
    });
  });

  describe("getBuildJob", () => {
    it("fetches build job status", async () => {
      server.use(
        http.get(`${API_BASE}/packages/jobs/1`, () =>
          HttpResponse.json(sampleBuildJob),
        ),
      );

      const { getBuildJob } = await loadPackageApi();
      const result = await getBuildJob(1);

      expect(result.id).toBe(1);
      expect(result.artifactId).toBe(100);
    });
  });

  describe("downloadArtifact", () => {
    it("downloads a blob with filename from content-disposition", async () => {
      server.use(
        http.get(`${API_BASE}/packages/artifacts/100/download`, () => {
          return new HttpResponse("file-content", {
            headers: {
              "Content-Type": "application/zip",
              "Content-Disposition": 'attachment; filename="export.zip"',
            },
          });
        }),
      );

      const { downloadArtifact } = await loadPackageApi();
      const result = await downloadArtifact(100);

      expect(result.filename).toBe("export.zip");
    });

    it("uses fallback filename when content-disposition is missing", async () => {
      server.use(
        http.get(`${API_BASE}/packages/artifacts/100/download`, () => {
          return new HttpResponse("file-content", {
            headers: { "Content-Type": "application/zip" },
          });
        }),
      );

      const { downloadArtifact } = await loadPackageApi();
      const result = await downloadArtifact(100);

      expect(result.filename).toBe("package-artifact-100.zip");
    });
  });

  describe("createSnapshot", () => {
    it("creates a data snapshot", async () => {
      server.use(
        http.post(`${API_BASE}/packages/workspaces/1/snapshots`, () =>
          HttpResponse.json(sampleSnapshot, { status: 201 }),
        ),
      );

      const { createSnapshot } = await loadPackageApi();
      const result = await createSnapshot(1, { datasetBinding: "ROSTER" });

      expect(result.id).toBe(1);
      expect(result.status).toBe("READY");
    });
  });

  describe("listSnapshots", () => {
    it("lists snapshots for a workspace", async () => {
      server.use(
        http.get(`${API_BASE}/packages/workspaces/1/snapshots`, () =>
          HttpResponse.json([sampleSnapshot]),
        ),
      );

      const { listSnapshots } = await loadPackageApi();
      const result = await listSnapshots(1);

      expect(result).toHaveLength(1);
      expect(result[0].datasetBinding).toBe("ROSTER");
    });
  });

  describe("reorderNode", () => {
    it("reorders a node and returns the workspace", async () => {
      server.use(
        http.post(`${API_BASE}/packages/workspaces/1/nodes/reorder`, () =>
          HttpResponse.json(sampleWorkspace),
        ),
      );

      const { reorderNode } = await loadPackageApi();
      const result = await reorderNode(1, {
        movedNodeId: 1,
        targetParentId: null,
        targetOrderIndex: 2,
      });

      expect(result.id).toBe(1);
      expect(result.nodes).toHaveLength(1);
    });
  });
});
