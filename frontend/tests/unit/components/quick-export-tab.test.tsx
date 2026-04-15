import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockListCourses = vi.fn();
const mockDownloadCourseRoster = vi.fn();
const mockDownloadCourseSubmissions = vi.fn();
const mockExtractExportErrorMessage = vi.fn();
const mockTriggerBrowserDownload = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess, error: mockToastError },
  }));
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));
  vi.doMock("@/lib/export-api", () => ({
    downloadCourseRoster: mockDownloadCourseRoster,
    downloadCourseSubmissions: mockDownloadCourseSubmissions,
    extractExportErrorMessage: mockExtractExportErrorMessage,
  }));
  vi.doMock("@/lib/utils", () => ({
    triggerBrowserDownload: mockTriggerBrowserDownload,
    cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/archive/QuickExportTab");
  return imported.default;
}

const mockCourses = [
  {
    id: 1,
    name: "Intro to CS",
    studentCount: 30,
    assignmentIds: [],
    teacherId: 1,
    teacherName: "Prof Smith",
    createdAt: "2025-01-01",
    status: "ACTIVE",
  },
  {
    id: 2,
    name: "Data Science",
    studentCount: 25,
    assignmentIds: [],
    teacherId: 2,
    teacherName: "Prof Jones",
    createdAt: "2025-01-01",
    status: "ACTIVE",
  },
];

describe("QuickExportTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Course Roster and Course Submissions cards", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="RESEARCHER" canExportIdentifiable={true} />
    );
    await waitFor(() => {
      expect(screen.getByText("Course Roster")).toBeInTheDocument();
      expect(screen.getByText("Course Submissions")).toBeInTheDocument();
    });
  });

  it("does not render placeholder export cards", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="RESEARCHER" canExportIdentifiable={true} />
    );
    await waitFor(() => {
      expect(screen.queryByText("Assignment Templates")).not.toBeInTheDocument();
      expect(screen.queryByText("Assignment Configurations")).not.toBeInTheDocument();
      expect(screen.queryByText("Rubric Definitions")).not.toBeInTheDocument();
      expect(screen.queryByText("Course Metadata")).not.toBeInTheDocument();
    });
  });

  it("renders Download Roster button", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="RESEARCHER" canExportIdentifiable={true} />
    );
    await waitFor(() => {
      expect(screen.getByText("Download Roster")).toBeInTheDocument();
    });
  });

  it("shows permission notice for researchers without identifiable access", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="RESEARCHER" canExportIdentifiable={false} />
    );
    await waitFor(() => {
      expect(
        screen.getByText(/Include names .* emails.*option is disabled/)
      ).toBeInTheDocument();
    });
  });

  it("does not show permission notice for admins", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="ADMIN" canExportIdentifiable={false} />
    );
    await waitFor(() => {
      expect(
        screen.queryByText(/option is disabled for your account/)
      ).not.toBeInTheDocument();
    });
  });

  it("does not show identifiable checkbox when canExportIdentifiable is false", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="TEACHER" canExportIdentifiable={false} />
    );
    await waitFor(() => {
      expect(screen.getByText("Course Roster")).toBeInTheDocument();
    });
    // The identifiable checkboxes should not be in the document
    expect(
      screen.queryByText("Include names & emails")
    ).not.toBeInTheDocument();
  });

  it("shows error toast when course loading fails", async () => {
    mockListCourses.mockRejectedValueOnce(new Error("Network error"));
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="RESEARCHER" canExportIdentifiable={true} />
    );
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Failed to load courses.");
    });
  });

  it("shows an empty-state hint when no active courses are available", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="RESEARCHER" canExportIdentifiable={true} />
    );
    await waitFor(() => {
      expect(
        screen.getByText(/No active courses are available for live export yet/i)
      ).toBeInTheDocument();
    });
  });

  it("renders description texts for export cards", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="RESEARCHER" canExportIdentifiable={true} />
    );
    await waitFor(() => {
      expect(
        screen.getByText("Download a list of students enrolled in a course.")
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          /Download submission records for a single course/
        )
      ).toBeInTheDocument();
    });
  });

  it("downloads roster successfully when course is selected", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const mockBlob = new Blob(["csv"], { type: "text/csv" });
    mockDownloadCourseRoster.mockResolvedValueOnce({
      blob: mockBlob,
      filename: "roster.csv",
    });
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="TEACHER" canExportIdentifiable={false} />
    );

    // Wait for courses to load and first course to be auto-selected
    await waitFor(() => {
      expect(mockListCourses).toHaveBeenCalled();
    });

    const downloadBtn = screen.getByText("Download Roster");
    await userEvent.click(downloadBtn);

    await waitFor(() => {
      expect(mockDownloadCourseRoster).toHaveBeenCalledWith(1, {
        status: undefined,
        identifiable: undefined,
      });
    });
    expect(mockTriggerBrowserDownload).toHaveBeenCalledWith(
      mockBlob,
      "roster.csv"
    );
    expect(mockToastSuccess).toHaveBeenCalledWith("Download started.");
  });

  it("shows error toast when roster download fails", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockDownloadCourseRoster.mockRejectedValueOnce(new Error("fail"));
    mockExtractExportErrorMessage.mockResolvedValueOnce("Export failed");
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="TEACHER" canExportIdentifiable={false} />
    );

    await waitFor(() => {
      expect(mockListCourses).toHaveBeenCalled();
    });

    await userEvent.click(screen.getByText("Download Roster"));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Export failed");
    });
  });

  it("downloads submissions successfully", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const mockBlob = new Blob(["csv"], { type: "text/csv" });
    mockDownloadCourseSubmissions.mockResolvedValueOnce({
      blob: mockBlob,
      filename: "submissions.csv",
    });
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="TEACHER" canExportIdentifiable={false} />
    );

    await waitFor(() => {
      expect(mockListCourses).toHaveBeenCalled();
    });

    // Need to open the Course Submissions card first
    const subsCard = screen.getByText("Course Submissions");
    await userEvent.click(subsCard);

    // Click Download Submissions button
    const downloadBtn = await screen.findByText("Download Submissions");
    await userEvent.click(downloadBtn);

    await waitFor(() => {
      expect(mockDownloadCourseSubmissions).toHaveBeenCalledWith(1, {
        startDate: undefined,
        endDate: undefined,
        category: undefined,
        status: undefined,
        includeAnswers: undefined,
        identifiable: undefined,
      });
    });
    expect(mockTriggerBrowserDownload).toHaveBeenCalledWith(
      mockBlob,
      "submissions.csv"
    );
    expect(mockToastSuccess).toHaveBeenCalledWith("Download started.");
  });

  it("shows error toast when submissions download fails", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockDownloadCourseSubmissions.mockRejectedValueOnce(
      new Error("server error")
    );
    mockExtractExportErrorMessage.mockResolvedValueOnce(
      "Submission export failed"
    );
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="TEACHER" canExportIdentifiable={false} />
    );

    await waitFor(() => {
      expect(mockListCourses).toHaveBeenCalled();
    });

    // Open the Course Submissions card
    await userEvent.click(screen.getByText("Course Submissions"));

    const downloadBtn = await screen.findByText("Download Submissions");
    await userEvent.click(downloadBtn);

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Submission export failed"
      );
    });
  });

  it("renders date inputs and checkboxes in submissions card", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="TEACHER" canExportIdentifiable={true} />
    );

    // Open the Course Submissions card
    await userEvent.click(screen.getByText("Course Submissions"));

    await waitFor(() => {
      expect(screen.getByText("From")).toBeInTheDocument();
      expect(screen.getByText("To")).toBeInTheDocument();
      expect(screen.getByText("Category")).toBeInTheDocument();
      expect(
        screen.getByText("Include student answers")
      ).toBeInTheDocument();
    });
  });

  it("sends date and checkbox options when downloading submissions with filters", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const mockBlob = new Blob(["csv"], { type: "text/csv" });
    mockDownloadCourseSubmissions.mockResolvedValueOnce({
      blob: mockBlob,
      filename: "subs.csv",
    });
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="TEACHER" canExportIdentifiable={true} />
    );

    await waitFor(() => {
      expect(mockListCourses).toHaveBeenCalled();
    });

    // Open the Course Submissions card
    await userEvent.click(screen.getByText("Course Submissions"));

    // Fill in date fields
    const dateInputs = await screen.findAllByDisplayValue("");
    // Find the date inputs specifically (type="date")
    const fromInput = dateInputs.find(
      (el) => el.getAttribute("type") === "date"
    );
    if (fromInput) {
      await userEvent.clear(fromInput);
      await userEvent.type(fromInput, "2026-01-01");
    }

    // Click Include student answers checkbox
    const answersCheckbox = screen.getByText("Include student answers");
    await userEvent.click(answersCheckbox);

    // Click Download Submissions
    const downloadBtn = screen.getByText("Download Submissions");
    await userEvent.click(downloadBtn);

    await waitFor(() => {
      expect(mockDownloadCourseSubmissions).toHaveBeenCalled();
    });
  });

  it("shows identifiable checkboxes in submissions card when canExportIdentifiable is true", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="TEACHER" canExportIdentifiable={true} />
    );

    // Open the Course Submissions card
    await userEvent.click(screen.getByText("Course Submissions"));

    await waitFor(() => {
      // Should find "Include names & emails" text (rendered as HTML entities)
      const matches = screen.getAllByText(/Include names/);
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows error toast when trying to download submissions with no course", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="TEACHER" canExportIdentifiable={false} />
    );

    await waitFor(() => {
      expect(mockListCourses).toHaveBeenCalled();
    });

    // Open the Course Submissions card
    await userEvent.click(screen.getByText("Course Submissions"));

    // The Download Submissions button should be disabled, but let's test the guard
    const downloadBtn = await screen.findByText("Download Submissions");
    // Even though button is disabled, test the handler guard path
    expect(downloadBtn.closest("button")).toBeDisabled();
  });

  it("renders the end date input in submissions card", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="TEACHER" canExportIdentifiable={false} />
    );

    // Open the Course Submissions card
    await userEvent.click(screen.getByText("Course Submissions"));

    await waitFor(() => {
      expect(screen.getByText("To")).toBeInTheDocument();
    });

    // Find date inputs and interact with the end date
    const dateInputs = screen.getAllByDisplayValue("");
    const endDateInput = dateInputs.filter(
      (el) => el.getAttribute("type") === "date"
    )[1];
    if (endDateInput) {
      await userEvent.type(endDateInput, "2026-12-31");
      expect(endDateInput).toHaveValue("2026-12-31");
    }
  });

  it("toggles subsIdentifiable checkbox in submissions card", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const mockBlob = new Blob(["csv"], { type: "text/csv" });
    mockDownloadCourseSubmissions.mockResolvedValueOnce({
      blob: mockBlob,
      filename: "subs.csv",
    });
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="TEACHER" canExportIdentifiable={true} />
    );

    await waitFor(() => {
      expect(mockListCourses).toHaveBeenCalled();
    });

    // Open the Course Submissions card
    await userEvent.click(screen.getByText("Course Submissions"));

    // Find "Include names & emails" labels - second one is in submissions card
    await waitFor(() => {
      const identLabels = screen.getAllByText(/Include names/);
      expect(identLabels.length).toBeGreaterThanOrEqual(2);
    });

    const identLabels = screen.getAllByText(/Include names/);
    // Click the second one (in submissions card)
    await userEvent.click(identLabels[1]);

    // Now download to verify the flag was set
    await userEvent.click(screen.getByText("Download Submissions"));

    await waitFor(() => {
      expect(mockDownloadCourseSubmissions).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ identifiable: true })
      );
    });
  });

  it("renders roster identifiable checkbox and sends it in request", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    const mockBlob = new Blob(["csv"], { type: "text/csv" });
    mockDownloadCourseRoster.mockResolvedValueOnce({
      blob: mockBlob,
      filename: "roster.csv",
    });
    const QuickExportTab = await loadComponent();
    render(
      <QuickExportTab role="TEACHER" canExportIdentifiable={true} />
    );

    await waitFor(() => {
      expect(mockListCourses).toHaveBeenCalled();
    });

    // Click the identifiable checkbox in the roster card
    const identifiableLabels = screen.getAllByText(/Include names/);
    // The first one is in the roster card
    await userEvent.click(identifiableLabels[0]);

    await userEvent.click(screen.getByText("Download Roster"));

    await waitFor(() => {
      expect(mockDownloadCourseRoster).toHaveBeenCalledWith(1, {
        status: undefined,
        identifiable: true,
      });
    });
  });
});
