import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGetSubmission = vi.fn();
const mockOverrideSubmissionScore = vi.fn();
const mockGetAssignment = vi.fn();
const mockGetAssignmentTemplate = vi.fn();
const mockToast = { success: vi.fn(), error: vi.fn() };

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
  }));
  vi.doMock("next/link", () => ({
    default: ({ children, ...props }: any) => <a {...props}>{children}</a>,
  }));
  vi.doMock("sonner", () => ({ toast: mockToast }));
  vi.doMock("@/lib/submission-api", () => ({
    getSubmission: mockGetSubmission,
    overrideSubmissionScore: mockOverrideSubmissionScore,
  }));
  vi.doMock("@/lib/assignment-api", () => ({
    getAssignment: mockGetAssignment,
    getAssignmentTemplate: mockGetAssignmentTemplate,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/submissions/SubmissionDetailView"
  );
  return imported.default;
}

const baseSubmission = {
  id: 1,
  assignmentId: 10,
  studentId: 42,
  teacherId: 5,
  submittedAt: "2026-02-15T14:30:00Z",
  score: 8,
  status: "GRADED" as const,
  answers: [
    {
      questionId: 100,
      type: "MULTIPLE_CHOICE" as const,
      data: { selected: [0] },
      score: 5,
    },
    {
      questionId: 101,
      type: "SHORT_ANSWER" as const,
      data: { text: "Sample answer" },
      score: 3,
    },
  ],
};

const baseAssignment = {
  id: 10,
  title: "Midterm Assessment",
  assessmentId: 20,
  assessmentTitle: "Midterm",
  audienceType: "COURSE",
  courseId: 1,
  targetTeacherId: null,
  openAt: null,
  dueAt: null,
  status: "ACTIVE",
};

const baseTemplate = {
  id: 20,
  title: "Midterm",
  category: "EXAM",
  gradingMode: "MANUAL" as const,
  scoringPolicy: "STANDARD" as const,
  questions: [
    {
      questionId: 100,
      id: 100,
      type: "MULTIPLE_CHOICE" as const,
      prompt: "What is 2+2?",
      maxPoints: 5,
      autoGradable: true,
      graded: true,
      data: {
        choices: [
          { prompt: "3", score: 0 },
          { prompt: "4", score: 5 },
        ],
      },
      selectAll: null,
      min: null,
      max: null,
      groupId: null,
      rubricId: null,
      gradingStrategy: "AUTO" as const,
    },
    {
      questionId: 101,
      id: 101,
      type: "SHORT_ANSWER" as const,
      prompt: "Explain gravity.",
      maxPoints: 5,
      autoGradable: false,
      graded: true,
      data: null,
      selectAll: null,
      min: null,
      max: null,
      groupId: null,
      rubricId: null,
      gradingStrategy: "MANUAL" as const,
    },
  ],
  questionGroups: [],
  rubricId: null,
};

describe("SubmissionDetailView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading spinner initially", async () => {
    // Never resolve to keep loading state
    mockGetSubmission.mockReturnValue(new Promise(() => {}));
    const Component = await loadComponent();
    const { container } = render(
      <Component submissionId={1} viewerRole="TEACHER" />
    );

    // Loader2 renders an svg with animate-spin class
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("shows error when submission fails to load", async () => {
    mockGetSubmission.mockRejectedValueOnce({
      response: { data: { detail: "Not found" } },
    });
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Not found")).toBeInTheDocument();
    });
    expect(screen.getByText("Back to Submissions")).toBeInTheDocument();
  });

  it("shows generic error when detail missing", async () => {
    mockGetSubmission.mockRejectedValueOnce(new Error("boom"));
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load submission.")
      ).toBeInTheDocument();
    });
  });

  it("renders submission detail after loading", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Submission #1")).toBeInTheDocument();
    });

    expect(screen.getByText("Midterm Assessment")).toBeInTheDocument();
    expect(screen.getByText("GRADED")).toBeInTheDocument();
    expect(screen.getByText("#42")).toBeInTheDocument();
    expect(screen.getByText("MANUAL")).toBeInTheDocument();
  });

  it("renders score and total points", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      // Score display: "8 / 10"
      expect(screen.getByText("8 / 10")).toBeInTheDocument();
    });
  });

  it("renders answers section with questions", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Answers")).toBeInTheDocument();
    });

    expect(
      screen.getByText("Q1. What is 2+2?")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Q2. Explain gravity.")
    ).toBeInTheDocument();
  });

  it("renders Multiple Choice answer with label", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      // selected[0] maps to choice "3"
      expect(screen.getByText("3")).toBeInTheDocument();
    });
  });

  it("renders Short Answer text", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Sample answer")).toBeInTheDocument();
    });
  });

  it("shows question type labels", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText(/Multiple Choice/)).toBeInTheDocument();
      expect(screen.getByText(/Short Answer/)).toBeInTheDocument();
    });
  });

  it("shows Save Scores button for TEACHER", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Save Scores/ })
      ).toBeInTheDocument();
    });
  });

  it("shows Save Scores button for ADMIN", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="ADMIN" />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Save Scores/ })
      ).toBeInTheDocument();
    });
  });

  it("does not show Save Scores for STUDENT", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.getByText("Submission #1")).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("button", { name: /Save Scores/ })
    ).not.toBeInTheDocument();
  });

  it("does not show Save Scores for RESEARCHER", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="RESEARCHER" />);

    await waitFor(() => {
      expect(screen.getByText("Submission #1")).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("button", { name: /Save Scores/ })
    ).not.toBeInTheDocument();
  });

  it("calls overrideSubmissionScore on Save Scores click", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);

    const updatedSubmission = {
      ...baseSubmission,
      answers: baseSubmission.answers.map((a) => ({
        ...a,
        score: 5,
      })),
    };
    mockOverrideSubmissionScore.mockResolvedValueOnce(updatedSubmission);

    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Save Scores/ })
      ).toBeInTheDocument();
    });

    await userEvent.click(
      screen.getByRole("button", { name: /Save Scores/ })
    );

    await waitFor(() => {
      expect(mockOverrideSubmissionScore).toHaveBeenCalledWith(1, [5, 3]);
    });
    expect(mockToast.success).toHaveBeenCalledWith("Scores updated.");
  });

  it("shows toast error when score override fails", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    mockOverrideSubmissionScore.mockRejectedValueOnce({
      response: { data: { detail: "Score exceeds max" } },
    });

    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Save Scores/ })
      ).toBeInTheDocument();
    });

    await userEvent.click(
      screen.getByRole("button", { name: /Save Scores/ })
    );

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith("Score exceeds max");
    });
  });

  it("shows 'No answers found' when answers array is empty", async () => {
    const emptySubmission = { ...baseSubmission, answers: [] };
    mockGetSubmission.mockResolvedValueOnce(emptySubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText("No answers found on this submission.")
      ).toBeInTheDocument();
    });
  });

  it("renders NUMBER_SCALE answer", async () => {
    const sub = {
      ...baseSubmission,
      answers: [
        {
          questionId: 102,
          type: "NUMBER_SCALE" as const,
          data: { val: 7 },
          score: 7,
        },
      ],
    };
    const tmpl = {
      ...baseTemplate,
      questions: [
        {
          ...baseTemplate.questions[0],
          questionId: 102,
          id: 102,
          type: "NUMBER_SCALE" as const,
          prompt: "Rate 1-10",
          maxPoints: 10,
        },
      ],
    };
    mockGetSubmission.mockResolvedValueOnce(sub);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(tmpl);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="STUDENT" />);

    await waitFor(() => {
      // "7" appears as both student response and score
      const sevens = screen.getAllByText("7");
      expect(sevens.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Number Scale/)).toBeInTheDocument();
    });
  });

  it("shows 'No option selected' for MC with empty selected", async () => {
    const sub = {
      ...baseSubmission,
      answers: [
        {
          questionId: 100,
          type: "MULTIPLE_CHOICE" as const,
          data: { selected: [] },
          score: 0,
        },
      ],
    };
    mockGetSubmission.mockResolvedValueOnce(sub);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.getByText("No option selected")).toBeInTheDocument();
    });
  });

  it("shows 'No response' for SHORT_ANSWER with empty text", async () => {
    const sub = {
      ...baseSubmission,
      answers: [
        {
          questionId: 101,
          type: "SHORT_ANSWER" as const,
          data: { text: "" },
          score: null,
        },
      ],
    };
    mockGetSubmission.mockResolvedValueOnce(sub);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.getByText("No response")).toBeInTheDocument();
    });
  });

  it("shows 'No value selected' for NUMBER_SCALE with null val", async () => {
    const sub = {
      ...baseSubmission,
      answers: [
        {
          questionId: 102,
          type: "NUMBER_SCALE" as const,
          data: { val: null },
          score: null,
        },
      ],
    };
    mockGetSubmission.mockResolvedValueOnce(sub);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce({
      ...baseTemplate,
      questions: [],
    });
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.getByText("No value selected")).toBeInTheDocument();
    });
  });

  it("shows HYBRID mode message", async () => {
    const hybridTemplate = { ...baseTemplate, gradingMode: "HYBRID" as const };
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(hybridTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText(
          "Hybrid mode: only short-answer question scores are editable."
        )
      ).toBeInTheDocument();
    });
  });

  it("shows override message for non-HYBRID mode", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText(
          "Override scores and save to mark this submission graded."
        )
      ).toBeInTheDocument();
    });
  });

  it("shows Back to Submissions link", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.getByText("Back to Submissions")).toBeInTheDocument();
    });
  });

  it("shows assignment fallback title when assignment is null", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce({ ...baseAssignment, title: "" });
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.getByText("Assignment #10")).toBeInTheDocument();
    });
  });

  it("shows toast error for NaN score input on save", async () => {
    mockGetSubmission.mockResolvedValueOnce(baseSubmission);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(baseTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Submission #1")).toBeInTheDocument();
    });

    // Find score inputs and type invalid value
    const inputs = screen.getAllByRole("textbox");
    await userEvent.clear(inputs[0]);
    await userEvent.type(inputs[0], "abc");

    await userEvent.click(
      screen.getByRole("button", { name: /Save Scores/ })
    );

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        "All score values must be valid non-negative numbers."
      );
    });
  });

  it("shows toast error for no gradable answers in HYBRID with no SHORT_ANSWER", async () => {
    const sub = {
      ...baseSubmission,
      answers: [
        {
          questionId: 100,
          type: "MULTIPLE_CHOICE" as const,
          data: { selected: [0] },
          score: 5,
        },
      ],
    };
    const hybridTemplate = { ...baseTemplate, gradingMode: "HYBRID" as const };
    mockGetSubmission.mockResolvedValueOnce(sub);
    mockGetAssignment.mockResolvedValueOnce(baseAssignment);
    mockGetAssignmentTemplate.mockResolvedValueOnce(hybridTemplate);
    const Component = await loadComponent();
    render(<Component submissionId={1} viewerRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Submission #1")).toBeInTheDocument();
    });

    await userEvent.click(
      screen.getByRole("button", { name: /Save Scores/ })
    );

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        "No gradable answers found for score override."
      );
    });
  });
});
