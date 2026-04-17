import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockListCodes = vi.fn();
const mockCreateCodes = vi.fn();
const mockToastError = vi.fn();
const mockToastSuccess = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    usePathname: () => "/dashboard/courses/1",
  }));
  vi.doMock("sonner", () => ({
    toast: {
      error: mockToastError,
      success: mockToastSuccess,
    },
  }));
  vi.doMock("@/lib/registration-code-api", () => ({
    listRegistrationCodes: mockListCodes,
    createRegistrationCodes: mockCreateCodes,
  }));
  // Mock sub-dialogs to simplify tests
  vi.doMock("@/components/codes/CreateRegistrationCodeDialog", () => ({
    CreateRegistrationCodeDialog: ({
      open,
      onSubmit,
    }: {
      open: boolean;
      onSubmit: (values: any) => void;
    }) =>
      open ? (
        <div data-testid="create-dialog">
          <button
            onClick={() =>
              onSubmit({
                codeType: "STUDENT",
                count: 1,
                usesPerCode: 1,
                expiresAt: "2026-12-31",
              })
            }
          >
            Submit Code
          </button>
        </div>
      ) : null,
  }));
  vi.doMock("@/components/codes/RegistrationCodeDialog", () => ({
    RegistrationCodeDialog: ({
      open,
      codes,
    }: {
      open: boolean;
      codes: string[];
    }) =>
      open ? (
        <div data-testid="code-dialog">
          {codes.map((c: string) => (
            <span key={c}>{c}</span>
          ))}
        </div>
      ) : null,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/courses/CourseRegistrationTab"
  );
  return imported.default;
}

const mockCodes = [
  {
    id: 1,
    code: null,
    codePrefix: "ABC1",
    codeType: "STUDENT" as const,
    status: "ACTIVE" as const,
    maxUses: 5,
    timesUsed: 2,
    usesRemaining: 3,
    expiresAt: "2026-12-31T00:00:00Z",
    isActive: true,
    courseId: 1,
    courseName: "Bio 101",
    metadata: null,
    createdByUserId: 1,
    createdAt: "2026-01-01T00:00:00Z",
    archivedAt: null,
  },
];

describe("CourseRegistrationTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", async () => {
    mockListCodes.mockReturnValue(new Promise(() => {}));
    const Component = await loadComponent();
    render(<Component courseId={1} />);
    expect(screen.getByText("Loading codes...")).toBeInTheDocument();
  });

  it("renders code table when codes exist", async () => {
    mockListCodes.mockResolvedValue({ results: mockCodes });
    const Component = await loadComponent();
    render(<Component courseId={1} />);
    await waitFor(() => {
      expect(screen.getByText("ABC1")).toBeInTheDocument();
    });
    expect(screen.getByText("2 / 5")).toBeInTheDocument();
  });

  it("shows empty state when no active codes", async () => {
    mockListCodes.mockResolvedValue({ results: [] });
    const Component = await loadComponent();
    render(<Component courseId={1} />);
    await waitFor(() => {
      expect(
        screen.getByText("No active registration codes for this course."),
      ).toBeInTheDocument();
    });
  });

  it("shows error state when API fails", async () => {
    mockListCodes.mockRejectedValue(new Error("fail"));
    const Component = await loadComponent();
    render(<Component courseId={1} />);
    await waitFor(() => {
      expect(
        screen.getByText("Failed to load registration codes."),
      ).toBeInTheDocument();
    });
  });

  it("filters codes by courseId and isActive", async () => {
    const mixedCodes = [
      ...mockCodes,
      { ...mockCodes[0], id: 2, courseId: 99, codePrefix: "OTHER" },
      {
        ...mockCodes[0],
        id: 3,
        courseId: 1,
        isActive: false,
        codePrefix: "INACT",
      },
    ];
    mockListCodes.mockResolvedValue({ results: mixedCodes });
    const Component = await loadComponent();
    render(<Component courseId={1} />);
    await waitFor(() => {
      expect(screen.getByText("ABC1")).toBeInTheDocument();
    });
    expect(screen.queryByText("OTHER")).toBeNull();
    expect(screen.queryByText("INACT")).toBeNull();
  });

  it("opens create dialog and handles successful code creation", async () => {
    const user = userEvent.setup();
    mockListCodes.mockResolvedValue({ results: [] });
    mockCreateCodes.mockResolvedValue({
      count: 1,
      codes: [{ ...mockCodes[0], code: "FULL-CODE-123" }],
    });
    const Component = await loadComponent();
    render(<Component courseId={1} />);
    await waitFor(() => {
      expect(screen.getByText("Generate Code")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Generate Code"));
    expect(screen.getByTestId("create-dialog")).toBeInTheDocument();

    // Re-mock listCodes for reload after creation
    mockListCodes.mockResolvedValue({ results: mockCodes });
    await user.click(screen.getByText("Submit Code"));
    await waitFor(() => {
      expect(screen.getByTestId("code-dialog")).toBeInTheDocument();
    });
    expect(screen.getByText("FULL-CODE-123")).toBeInTheDocument();
  });

  it("shows toast error when creation fails", async () => {
    const user = userEvent.setup();
    mockListCodes.mockResolvedValue({ results: [] });
    mockCreateCodes.mockRejectedValue({
      response: { data: { detail: "Server error" } },
    });
    const Component = await loadComponent();
    render(<Component courseId={1} />);
    await waitFor(() => {
      expect(screen.getByText("Generate Code")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Generate Code"));
    await user.click(screen.getByText("Submit Code"));
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Server error");
    });
  });

  it("shows fallback toast error when no detail in error", async () => {
    const user = userEvent.setup();
    mockListCodes.mockResolvedValue({ results: [] });
    mockCreateCodes.mockRejectedValue(new Error("generic"));
    const Component = await loadComponent();
    render(<Component courseId={1} />);
    await waitFor(() => {
      expect(screen.getByText("Generate Code")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Generate Code"));
    await user.click(screen.getByText("Submit Code"));
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Failed to generate registration code.",
      );
    });
  });

  it("shows toast error when server returns empty codes array", async () => {
    const user = userEvent.setup();
    mockListCodes.mockResolvedValue({ results: [] });
    mockCreateCodes.mockResolvedValue({ count: 0, codes: [] });
    const Component = await loadComponent();
    render(<Component courseId={1} />);
    await waitFor(() => {
      expect(screen.getByText("Generate Code")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Generate Code"));
    await user.click(screen.getByText("Submit Code"));
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalled();
    });
  });
});
