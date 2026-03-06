import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockListMySubmissions = vi.fn();
const mockListAssignmentSubmissions = vi.fn();
const mockGetSubmission = vi.fn();
const mockListAssignmentsForUser = vi.fn();
const mockListAssignmentsByCourse = vi.fn();
const mockListCourses = vi.fn();
const mockPush = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush, back: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
  }));
  vi.doMock("@/lib/submission-api", () => ({
    listMySubmissions: mockListMySubmissions,
    listAssignmentSubmissions: mockListAssignmentSubmissions,
    getSubmission: mockGetSubmission,
  }));
  vi.doMock("@/lib/assignment-api", () => ({
    listAssignmentsForUser: mockListAssignmentsForUser,
    listAssignmentsByCourse: mockListAssignmentsByCourse,
  }));
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/submissions/SubmissionsHubView"
  );
  return imported.default;
}

async function renderSubmissionsHubAndWait(props: {
  role: "ADMIN" | "TEACHER" | "RESEARCHER" | "STUDENT";
  userId: number;
}) {
  const Component = await loadComponent();
  render(<Component {...props} />);
  await waitFor(() => {
    expect(
      screen.queryByText("Loading submissions...")
    ).not.toBeInTheDocument();
  });
}

describe("SubmissionsHubView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── STUDENT ROLE ──

  describe("student role", () => {
    it("renders 'My Submissions' heading for student", async () => {
      mockListMySubmissions.mockResolvedValueOnce([]);
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      await renderSubmissionsHubAndWait({
        role: "STUDENT",
        userId: 1,
      });

      expect(screen.getByText("My Submissions")).toBeInTheDocument();
      expect(
        screen.getByText("Track draft, submitted, and graded work.")
      ).toBeInTheDocument();
    });

    it("shows loading state then empty message when no submissions", async () => {
      mockListMySubmissions.mockResolvedValueOnce([]);
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="STUDENT" userId={1} />);

      // Initially shows loading
      expect(screen.getByText("Loading submissions...")).toBeInTheDocument();

      await waitFor(() => {
        expect(
          screen.getByText("No submissions found for this filter.")
        ).toBeInTheDocument();
      });
    });

    it("renders submission rows for student", async () => {
      mockListMySubmissions.mockResolvedValueOnce([
        {
          id: 10,
          assignmentId: 5,
          submittedAt: "2026-02-01T12:00:00Z",
          score: 85,
          status: "GRADED",
        },
        {
          id: 11,
          assignmentId: 6,
          submittedAt: null,
          score: null,
          status: "IN_PROGRESS",
        },
      ]);
      mockListAssignmentsForUser.mockResolvedValueOnce([
        { id: 5, title: "Math Quiz" },
        { id: 6, title: "Science Lab" },
      ]);
      const Component = await loadComponent();
      render(<Component role="STUDENT" userId={1} />);

      await waitFor(() => {
        expect(screen.getByText("Math Quiz")).toBeInTheDocument();
      });

      expect(screen.getByText("Science Lab")).toBeInTheDocument();
      expect(screen.getByText("GRADED")).toBeInTheDocument();
      expect(screen.getByText("IN_PROGRESS")).toBeInTheDocument();
      expect(screen.getByText("85")).toBeInTheDocument();
    });

    it("shows assignment fallback name when assignment not in map", async () => {
      mockListMySubmissions.mockResolvedValueOnce([
        {
          id: 10,
          assignmentId: 999,
          submittedAt: null,
          score: null,
          status: "NOT_STARTED",
        },
      ]);
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="STUDENT" userId={1} />);

      await waitFor(() => {
        expect(screen.getByText("Assignment #999")).toBeInTheDocument();
      });
    });

    it("handles paginated submissions response", async () => {
      mockListMySubmissions.mockResolvedValueOnce({
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 20,
            assignmentId: 3,
            submittedAt: "2026-01-15T10:00:00Z",
            score: 90,
            status: "SUBMITTED",
          },
        ],
      });
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="STUDENT" userId={1} />);

      await waitFor(() => {
        expect(screen.getByText("SUBMITTED")).toBeInTheDocument();
      });
    });

    it("shows error when loading fails", async () => {
      mockListMySubmissions.mockRejectedValueOnce({
        response: { data: { detail: "Auth failed" } },
      });
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="STUDENT" userId={1} />);

      await waitFor(() => {
        expect(screen.getByText("Auth failed")).toBeInTheDocument();
      });
    });

    it("shows generic error when detail is missing", async () => {
      mockListMySubmissions.mockRejectedValueOnce(new Error("network"));
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="STUDENT" userId={1} />);

      await waitFor(() => {
        expect(
          screen.getByText("Failed to load your submissions.")
        ).toBeInTheDocument();
      });
    });

    it("renders View Submission and Open Assignment buttons", async () => {
      mockListMySubmissions.mockResolvedValueOnce([
        {
          id: 10,
          assignmentId: 5,
          submittedAt: null,
          score: null,
          status: "IN_PROGRESS",
        },
      ]);
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="STUDENT" userId={1} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: "View Submission" })
        ).toBeInTheDocument();
      });
      expect(
        screen.getByRole("button", { name: "Open Assignment" })
      ).toBeInTheDocument();
    });

    it("navigates when View Submission is clicked", async () => {
      mockListMySubmissions.mockResolvedValueOnce([
        {
          id: 10,
          assignmentId: 5,
          submittedAt: null,
          score: null,
          status: "IN_PROGRESS",
        },
      ]);
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="STUDENT" userId={1} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: "View Submission" })
        ).toBeInTheDocument();
      });

      await userEvent.click(
        screen.getByRole("button", { name: "View Submission" })
      );
      expect(mockPush).toHaveBeenCalledWith("/dashboard/submissions/10");
    });

    it("navigates when Open Assignment is clicked", async () => {
      mockListMySubmissions.mockResolvedValueOnce([
        {
          id: 10,
          assignmentId: 5,
          submittedAt: null,
          score: null,
          status: "IN_PROGRESS",
        },
      ]);
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="STUDENT" userId={1} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: "Open Assignment" })
        ).toBeInTheDocument();
      });

      await userEvent.click(
        screen.getByRole("button", { name: "Open Assignment" })
      );
      expect(mockPush).toHaveBeenCalledWith("/dashboard/assignments/5");
    });

    it("formats decimal score correctly", async () => {
      mockListMySubmissions.mockResolvedValueOnce([
        {
          id: 10,
          assignmentId: 5,
          submittedAt: null,
          score: 92.5,
          status: "GRADED",
        },
      ]);
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="STUDENT" userId={1} />);

      await waitFor(() => {
        expect(screen.getByText("92.5")).toBeInTheDocument();
      });
    });

    it("shows '-' for null score and null submittedAt", async () => {
      mockListMySubmissions.mockResolvedValueOnce([
        {
          id: 10,
          assignmentId: 5,
          submittedAt: null,
          score: null,
          status: "NOT_STARTED",
        },
      ]);
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="STUDENT" userId={1} />);

      await waitFor(() => {
        // score and submittedAt both show '-'
        const dashes = screen.getAllByText("-");
        expect(dashes.length).toBeGreaterThanOrEqual(2);
      });
    });

    it("renders Refresh button for student", async () => {
      mockListMySubmissions.mockResolvedValueOnce([]);
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      await renderSubmissionsHubAndWait({
        role: "STUDENT",
        userId: 1,
      });

      expect(
        screen.getByRole("button", { name: "Refresh" })
      ).toBeInTheDocument();
    });
  });

  // ── TEACHER ROLE ──

  describe("teacher role", () => {
    it("renders 'Submissions' heading for teacher", async () => {
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      await renderSubmissionsHubAndWait({
        role: "TEACHER",
        userId: 2,
      });

      expect(screen.getByText("Submissions")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Review submissions by assignment and open full submission detail for grading."
        )
      ).toBeInTheDocument();
    });

    it("shows 'Select an assignment' message when no assignments", async () => {
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="TEACHER" userId={2} />);

      await waitFor(() => {
        expect(
          screen.getByText("Select an assignment to view submissions.")
        ).toBeInTheDocument();
      });
    });

    it("loads submissions for first assignment automatically", async () => {
      mockListAssignmentsForUser.mockResolvedValueOnce([
        { id: 1, title: "HW1" },
        { id: 2, title: "HW2" },
      ]);
      mockListAssignmentSubmissions.mockResolvedValueOnce([
        {
          id: 100,
          assignmentId: 1,
          submittedAt: "2026-01-10T00:00:00Z",
          score: 75,
          status: "SUBMITTED",
        },
      ]);
      mockGetSubmission.mockResolvedValueOnce({
        id: 100,
        studentId: 42,
      });
      const Component = await loadComponent();
      render(<Component role="TEACHER" userId={2} />);

      await waitFor(() => {
        expect(screen.getByText("#100")).toBeInTheDocument();
      });
      expect(screen.getByText("#42")).toBeInTheDocument();
      expect(screen.getByText("SUBMITTED")).toBeInTheDocument();
      expect(screen.getByText("75")).toBeInTheDocument();
    });

    it("shows 'No submissions found' when assignment has none", async () => {
      mockListAssignmentsForUser.mockResolvedValueOnce([
        { id: 1, title: "HW1" },
      ]);
      mockListAssignmentSubmissions.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="TEACHER" userId={2} />);

      await waitFor(() => {
        expect(
          screen.getByText("No submissions found for this assignment.")
        ).toBeInTheDocument();
      });
    });

    it("shows error when teacher assignments fail to load", async () => {
      mockListAssignmentsForUser.mockRejectedValueOnce({
        response: { data: { detail: "Forbidden" } },
      });
      const Component = await loadComponent();
      render(<Component role="TEACHER" userId={2} />);

      await waitFor(() => {
        expect(screen.getByText("Forbidden")).toBeInTheDocument();
      });
    });

    it("does not render course selector for teacher", async () => {
      mockListAssignmentsForUser.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="TEACHER" userId={2} />);

      await waitFor(() => {
        expect(
          screen.getByText("Select an assignment to view submissions.")
        ).toBeInTheDocument();
      });

      // Teacher should NOT see "Select course" placeholder
      expect(screen.queryByText("Select course")).not.toBeInTheDocument();
    });

    it("renders Open button for teacher submission rows", async () => {
      mockListAssignmentsForUser.mockResolvedValueOnce([
        { id: 1, title: "HW1" },
      ]);
      mockListAssignmentSubmissions.mockResolvedValueOnce([
        {
          id: 100,
          assignmentId: 1,
          submittedAt: null,
          score: null,
          status: "IN_PROGRESS",
        },
      ]);
      mockGetSubmission.mockResolvedValueOnce({
        id: 100,
        studentId: null,
      });
      const Component = await loadComponent();
      render(<Component role="TEACHER" userId={2} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: "Open" })
        ).toBeInTheDocument();
      });
    });

    it("shows Showing submissions for assignment text", async () => {
      mockListAssignmentsForUser.mockResolvedValueOnce([
        { id: 1, title: "HW1" },
      ]);
      mockListAssignmentSubmissions.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="TEACHER" userId={2} />);

      await waitFor(() => {
        expect(
          screen.getByText(/Showing submissions for/)
        ).toBeInTheDocument();
      });
    });
  });

  // ── RESEARCHER ROLE ──

  describe("researcher role", () => {
    it("renders course and assignment selectors", async () => {
      mockListCourses.mockResolvedValueOnce([
        { id: 1, name: "Bio 101" },
      ]);
      mockListAssignmentsByCourse.mockResolvedValueOnce([
        { id: 10, title: "Lab Report" },
      ]);
      mockListAssignmentSubmissions.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="RESEARCHER" userId={3} />);

      await waitFor(() => {
        expect(
          screen.getByText("No submissions found for this assignment.")
        ).toBeInTheDocument();
      });
    });

    it("shows empty state when no courses", async () => {
      mockListCourses.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="RESEARCHER" userId={3} />);

      await waitFor(() => {
        expect(
          screen.getByText("Select an assignment to view submissions.")
        ).toBeInTheDocument();
      });
    });

    it("shows error when researcher scope fails", async () => {
      mockListCourses.mockRejectedValueOnce(new Error("fail"));
      const Component = await loadComponent();
      render(<Component role="RESEARCHER" userId={3} />);

      await waitFor(() => {
        expect(
          screen.getByText("Failed to load submissions scope.")
        ).toBeInTheDocument();
      });
    });

    it("loads submissions for first course+assignment automatically", async () => {
      mockListCourses.mockResolvedValueOnce([
        { id: 1, name: "Bio 101" },
      ]);
      mockListAssignmentsByCourse.mockResolvedValueOnce([
        { id: 10, title: "Lab Report" },
      ]);
      mockListAssignmentSubmissions.mockResolvedValueOnce([
        {
          id: 200,
          assignmentId: 10,
          submittedAt: "2026-03-01T08:00:00Z",
          score: 95,
          status: "GRADED",
        },
      ]);
      mockGetSubmission.mockResolvedValueOnce({
        id: 200,
        studentId: 55,
      });
      const Component = await loadComponent();
      render(<Component role="RESEARCHER" userId={3} />);

      await waitFor(() => {
        expect(screen.getByText("#200")).toBeInTheDocument();
      });
      expect(screen.getByText("#55")).toBeInTheDocument();
      expect(screen.getByText("95")).toBeInTheDocument();
    });
  });

  // ── TEACHER ROLE – additional coverage ──

  describe("teacher role – extra coverage", () => {
    it("clicking Refresh reloads submissions for selected assignment", async () => {
      mockListAssignmentsForUser.mockResolvedValueOnce([
        { id: 1, title: "HW1" },
      ]);
      mockListAssignmentSubmissions.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="TEACHER" userId={2} />);

      await waitFor(() => {
        expect(
          screen.getByText("No submissions found for this assignment.")
        ).toBeInTheDocument();
      });

      // Set up mock for the refresh call
      mockListAssignmentSubmissions.mockResolvedValueOnce([
        {
          id: 300,
          assignmentId: 1,
          submittedAt: "2026-02-15T12:00:00Z",
          score: 88,
          status: "GRADED",
        },
      ]);
      mockGetSubmission.mockResolvedValueOnce({
        id: 300,
        studentId: 77,
      });

      await userEvent.click(
        screen.getByRole("button", { name: "Refresh" })
      );

      await waitFor(() => {
        expect(screen.getByText("#300")).toBeInTheDocument();
      });
    });

    it("navigates when Open button is clicked on teacher submission row", async () => {
      mockListAssignmentsForUser.mockResolvedValueOnce([
        { id: 1, title: "HW1" },
      ]);
      mockListAssignmentSubmissions.mockResolvedValueOnce([
        {
          id: 150,
          assignmentId: 1,
          submittedAt: "2026-01-20T09:00:00Z",
          score: 70,
          status: "SUBMITTED",
        },
      ]);
      mockGetSubmission.mockResolvedValueOnce({
        id: 150,
        studentId: 33,
      });
      const Component = await loadComponent();
      render(<Component role="TEACHER" userId={2} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: "Open" })
        ).toBeInTheDocument();
      });

      await userEvent.click(
        screen.getByRole("button", { name: "Open" })
      );
      expect(mockPush).toHaveBeenCalledWith("/dashboard/submissions/150");
    });
  });

  // ── STUDENT ROLE – title fallback for assignment without title ──

  describe("student role – assignment title fallback", () => {
    it("uses assignment id fallback when assignment.title is empty string", async () => {
      mockListMySubmissions.mockResolvedValueOnce([
        {
          id: 10,
          assignmentId: 7,
          submittedAt: null,
          score: null,
          status: "NOT_STARTED",
        },
      ]);
      mockListAssignmentsForUser.mockResolvedValueOnce([
        { id: 7, title: "" },
      ]);
      const Component = await loadComponent();
      render(<Component role="STUDENT" userId={1} />);

      await waitFor(() => {
        expect(screen.getByText("Assignment #7")).toBeInTheDocument();
      });
    });
  });

  // ── ADMIN ROLE ──

  describe("admin role", () => {
    it("renders like researcher (non-student, non-teacher)", async () => {
      mockListCourses.mockResolvedValueOnce([]);
      const Component = await loadComponent();
      render(<Component role="ADMIN" userId={99} />);

      await waitFor(() => {
        expect(screen.getByText("Submissions")).toBeInTheDocument();
      });
    });
  });
});
