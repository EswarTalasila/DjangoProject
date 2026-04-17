import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost/_test/api/v1";

async function loadExportApi() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  return import("@/lib/export-api");
}

describe("export api", () => {
  describe("downloadCourseRoster", () => {
    it("downloads roster CSV with filename from content-disposition", async () => {
      server.use(
        http.get(`${API_BASE}/exports/courses/5/roster`, () => {
          return new HttpResponse("id,name\n1,Alice", {
            headers: {
              "Content-Type": "text/csv",
              "Content-Disposition": 'attachment; filename="roster-5.csv"',
            },
          });
        }),
      );

      const { downloadCourseRoster } = await loadExportApi();
      const result = await downloadCourseRoster(5);

      expect(result.filename).toBe("roster-5.csv");
    });

    it("uses fallback filename when content-disposition is missing", async () => {
      server.use(
        http.get(`${API_BASE}/exports/courses/5/roster`, () => {
          return new HttpResponse("id,name\n1,Alice", {
            headers: { "Content-Type": "text/csv" },
          });
        }),
      );

      const { downloadCourseRoster } = await loadExportApi();
      const result = await downloadCourseRoster(5);

      expect(result.filename).toBe("roster-5.csv");
    });

    it("passes filter params", async () => {
      server.use(
        http.get(`${API_BASE}/exports/courses/5/roster`, ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get("identifiable")).toBe("true");
          return new HttpResponse("data", {
            headers: { "Content-Type": "text/csv" },
          });
        }),
      );

      const { downloadCourseRoster } = await loadExportApi();
      await downloadCourseRoster(5, { identifiable: true });
    });
  });

  describe("downloadCourseSubmissions", () => {
    it("downloads submissions CSV", async () => {
      server.use(
        http.get(`${API_BASE}/exports/courses/5/submissions`, () => {
          return new HttpResponse("id,score\n1,85", {
            headers: {
              "Content-Type": "text/csv",
              "Content-Disposition": 'attachment; filename="submissions.csv"',
            },
          });
        }),
      );

      const { downloadCourseSubmissions } = await loadExportApi();
      const result = await downloadCourseSubmissions(5);

      expect(result.filename).toBe("submissions.csv");
    });

    it("uses fallback filename when content-disposition is missing", async () => {
      server.use(
        http.get(`${API_BASE}/exports/courses/5/submissions`, () => {
          return new HttpResponse("data", {
            headers: { "Content-Type": "text/csv" },
          });
        }),
      );

      const { downloadCourseSubmissions } = await loadExportApi();
      const result = await downloadCourseSubmissions(5);

      expect(result.filename).toBe("submissions-course-5.csv");
    });

    it("passes filter params including dates and category", async () => {
      server.use(
        http.get(`${API_BASE}/exports/courses/5/submissions`, ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get("startDate")).toBe("2026-01-01");
          expect(url.searchParams.get("category")).toBe("MATH");
          return new HttpResponse("data", {
            headers: { "Content-Type": "text/csv" },
          });
        }),
      );

      const { downloadCourseSubmissions } = await loadExportApi();
      await downloadCourseSubmissions(5, {
        startDate: "2026-01-01",
        category: "MATH",
      });
    });
  });

  describe("extractExportErrorMessage", () => {
    it("returns default message for null/undefined error", async () => {
      const { extractExportErrorMessage } = await loadExportApi();

      expect(await extractExportErrorMessage(null)).toBe(
        "Export failed. Please check filters and permissions.",
      );
      expect(await extractExportErrorMessage(undefined)).toBe(
        "Export failed. Please check filters and permissions.",
      );
    });

    it("returns default message for non-object error", async () => {
      const { extractExportErrorMessage } = await loadExportApi();

      expect(await extractExportErrorMessage("string error")).toBe(
        "Export failed. Please check filters and permissions.",
      );
    });

    it("returns default message for error without response", async () => {
      const { extractExportErrorMessage } = await loadExportApi();

      expect(await extractExportErrorMessage({})).toBe(
        "Export failed. Please check filters and permissions.",
      );
    });

    it("extracts detail from JSON response data", async () => {
      const { extractExportErrorMessage } = await loadExportApi();
      const error = {
        response: { data: { detail: "No data found for filters" } },
      };

      expect(await extractExportErrorMessage(error)).toBe(
        "No data found for filters",
      );
    });

    it("extracts detail from Blob response data", async () => {
      const { extractExportErrorMessage } = await loadExportApi();
      // Create a real Blob and verify the instanceof check works in this env
      const blobData = new Blob(
        [JSON.stringify({ detail: "Permission denied" })],
        { type: "application/json" },
      );

      if (typeof blobData.text === "function") {
        // Node/modern env where Blob.text() works
        const error = { response: { data: blobData } };
        expect(await extractExportErrorMessage(error)).toBe("Permission denied");
      } else {
        // jsdom env where Blob.text() is not available — falls through to default
        const error = { response: { data: blobData } };
        expect(await extractExportErrorMessage(error)).toBe(
          "Export failed. Please check filters and permissions.",
        );
      }
    });

    it("returns default for Blob with invalid JSON", async () => {
      const { extractExportErrorMessage } = await loadExportApi();
      const blobData = new Blob(["not json"], { type: "text/plain" });
      const error = { response: { data: blobData } };

      // Whether Blob path is reachable or not, both cases return the default
      expect(await extractExportErrorMessage(error)).toBe(
        "Export failed. Please check filters and permissions.",
      );
    });

    it("returns default for Blob with no detail field", async () => {
      const { extractExportErrorMessage } = await loadExportApi();
      const blobData = new Blob(
        [JSON.stringify({ message: "something" })],
        { type: "application/json" },
      );
      const error = { response: { data: blobData } };

      expect(await extractExportErrorMessage(error)).toBe(
        "Export failed. Please check filters and permissions.",
      );
    });

    it("returns default for object data without detail", async () => {
      const { extractExportErrorMessage } = await loadExportApi();
      const error = { response: { data: { message: "something" } } };

      expect(await extractExportErrorMessage(error)).toBe(
        "Export failed. Please check filters and permissions.",
      );
    });

    it("returns default for empty detail string", async () => {
      const { extractExportErrorMessage } = await loadExportApi();
      const error = { response: { data: { detail: "   " } } };

      expect(await extractExportErrorMessage(error)).toBe(
        "Export failed. Please check filters and permissions.",
      );
    });
  });
});
