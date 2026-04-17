import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockGetRubric = vi.fn();
const mockCreateRubric = vi.fn();
const mockUpdateRubric = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

function setupModuleMocks(searchParams = "") {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
    useSearchParams: () => new URLSearchParams(searchParams),
  }));
  vi.doMock("@/lib/rubric-api", () => ({
    getRubric: mockGetRubric,
    createRubric: mockCreateRubric,
    updateRubric: mockUpdateRubric,
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess, error: mockToastError },
  }));
}

async function loadComponent(searchParams = "") {
  vi.resetModules();
  setupModuleMocks(searchParams);
  const imported = await import("@/components/rubrics/RubricBuilderForm");
  return imported.default;
}

function submitForm() {
  const form = document.querySelector("form")!;
  fireEvent.submit(form);
}

describe("RubricBuilderForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("create mode", () => {
    it("renders form with title and description inputs", async () => {
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="create" />);
      expect(screen.getByLabelText("Title")).toBeInTheDocument();
      expect(screen.getByLabelText("Description")).toBeInTheDocument();
    });

    it("renders Rubric Details heading", async () => {
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="create" />);
      expect(screen.getByText("Rubric Details")).toBeInTheDocument();
    });

    it("renders Create Rubric submit button", async () => {
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="create" />);
      expect(screen.getByRole("button", { name: /create rubric/i })).toBeInTheDocument();
    });

    it("renders Cancel button", async () => {
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="create" />);
      expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
    });

    it("shows one default criterion", async () => {
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="create" />);
      expect(screen.getByText("Criteria (1)")).toBeInTheDocument();
      expect(screen.getAllByText("Criterion 1").length).toBeGreaterThanOrEqual(1);
    });

    it("adds a criterion when Add Criterion is clicked", async () => {
      const RubricBuilderForm = await loadComponent();
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);
      await user.click(screen.getByRole("button", { name: /add criterion/i }));
      expect(screen.getByText("Criteria (2)")).toBeInTheDocument();
    });

    it("shows validation error when title is empty on submit", async () => {
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="create" />);
      submitForm();
      expect(screen.getByText("Title is required")).toBeInTheDocument();
      expect(mockCreateRubric).not.toHaveBeenCalled();
    });

    it("shows validation error when criterion title is empty on submit", async () => {
      const RubricBuilderForm = await loadComponent();
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);

      await user.type(screen.getByLabelText("Title"), "My Rubric");
      submitForm();
      expect(screen.getByText("Every criterion must have a title")).toBeInTheDocument();
      expect(mockCreateRubric).not.toHaveBeenCalled();
    });

    it("submits successfully with valid data", async () => {
      mockCreateRubric.mockResolvedValueOnce({ id: 99 });
      const RubricBuilderForm = await loadComponent();
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);

      await user.type(screen.getByLabelText("Title"), "My Rubric");
      await user.type(screen.getByPlaceholderText("Criterion title..."), "Grammar");

      submitForm();

      await waitFor(() => {
        expect(mockCreateRubric).toHaveBeenCalledOnce();
      });
      expect(mockToastSuccess).toHaveBeenCalledWith("Rubric created");
      expect(mockPush).toHaveBeenCalledWith("/dashboard/rubrics/99");
    });

    it("navigates to returnTo URL with rubric ID on create", async () => {
      mockCreateRubric.mockResolvedValueOnce({ id: 50 });
      const RubricBuilderForm = await loadComponent("returnTo=/dashboard/assignment-templates/new");
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);

      await user.type(screen.getByLabelText("Title"), "My Rubric");
      await user.type(screen.getByPlaceholderText("Criterion title..."), "Grammar");
      submitForm();

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/dashboard/assignment-templates/new?newRubricId=50");
      });
    });

    it("appends newRubricId with & if returnTo already has query params", async () => {
      mockCreateRubric.mockResolvedValueOnce({ id: 50 });
      const RubricBuilderForm = await loadComponent("returnTo=/dashboard/assignment-templates/new?existing=1");
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);

      await user.type(screen.getByLabelText("Title"), "My Rubric");
      await user.type(screen.getByPlaceholderText("Criterion title..."), "Grammar");
      submitForm();

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/dashboard/assignment-templates/new?existing=1&newRubricId=50");
      });
    });

    it("shows error toast on create failure", async () => {
      mockCreateRubric.mockRejectedValueOnce({ response: { data: { detail: "Server error" } } });
      const RubricBuilderForm = await loadComponent();
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);

      await user.type(screen.getByLabelText("Title"), "My Rubric");
      await user.type(screen.getByPlaceholderText("Criterion title..."), "Grammar");
      submitForm();

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith("Server error");
      });
    });

    it("shows fallback error message when no detail", async () => {
      mockCreateRubric.mockRejectedValueOnce(new Error("fail"));
      const RubricBuilderForm = await loadComponent();
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);

      await user.type(screen.getByLabelText("Title"), "My Rubric");
      await user.type(screen.getByPlaceholderText("Criterion title..."), "Grammar");
      submitForm();

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith("Failed to save rubric");
      });
    });

    it("cancel navigates to rubrics list in create mode", async () => {
      const RubricBuilderForm = await loadComponent();
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);
      await user.click(screen.getByRole("button", { name: /cancel/i }));
      expect(mockPush).toHaveBeenCalledWith("/dashboard/rubrics");
    });

    it("cancel navigates to returnTo if provided", async () => {
      const RubricBuilderForm = await loadComponent("returnTo=/dashboard/assignment-templates/5");
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);
      await user.click(screen.getByRole("button", { name: /cancel/i }));
      expect(mockPush).toHaveBeenCalledWith("/dashboard/assignment-templates/5");
    });

    it("ignores returnTo that does not start with /dashboard/assignment-templates", async () => {
      const RubricBuilderForm = await loadComponent("returnTo=/evil/path");
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);
      await user.click(screen.getByRole("button", { name: /cancel/i }));
      expect(mockPush).toHaveBeenCalledWith("/dashboard/rubrics");
    });

    it("toggles tips section", async () => {
      const RubricBuilderForm = await loadComponent();
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);

      expect(screen.getByText(/Define criteria as rows/)).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: /hide tips/i }));
      expect(screen.queryByText(/Define criteria as rows/)).not.toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: /show tips/i }));
      expect(screen.getByText(/Define criteria as rows/)).toBeInTheDocument();
    });

    it("clears title error when user types", async () => {
      const RubricBuilderForm = await loadComponent();
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);

      submitForm();
      expect(screen.getByText("Title is required")).toBeInTheDocument();

      await user.type(screen.getByLabelText("Title"), "R");
      expect(screen.queryByText("Title is required")).not.toBeInTheDocument();
    });

    it("validates that at least one criterion exists", async () => {
      const RubricBuilderForm = await loadComponent();
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="create" />);

      await user.type(screen.getByLabelText("Title"), "My Rubric");

      // Remove the default criterion by clicking its trash button
      const allButtons = screen.getAllByRole("button");
      const criterionTrashBtn = allButtons.find(
        (b) => b.className.includes("text-destructive") && !b.textContent?.includes("Remove level")
      );
      if (criterionTrashBtn) {
        await user.click(criterionTrashBtn);
      }

      submitForm();
      expect(screen.getByText("At least one criterion is required")).toBeInTheDocument();
    });
  });

  describe("edit mode", () => {
    it("shows loading spinner initially", async () => {
      mockGetRubric.mockImplementation(() => new Promise(() => {}));
      const RubricBuilderForm = await loadComponent();
      const { container } = render(<RubricBuilderForm mode="edit" rubricId={1} />);
      expect(container.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("loads and populates rubric data", async () => {
      mockGetRubric.mockResolvedValueOnce({
        id: 1,
        title: "Existing Rubric",
        description: "Existing description",
        criteria: [
          {
            id: 10,
            title: "Grammar",
            description: "Grammar usage",
            weight: 2,
            orderIndex: 0,
            levels: [
              { id: 100, label: "Great", points: 5, description: "Perfect", orderIndex: 0 },
            ],
          },
        ],
      });
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="edit" rubricId={1} />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("Existing Rubric")).toBeInTheDocument();
      });
      expect(screen.getByDisplayValue("Existing description")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Grammar")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Great")).toBeInTheDocument();
    });

    it("shows Save Changes button in edit mode", async () => {
      mockGetRubric.mockResolvedValueOnce({
        id: 1,
        title: "Test",
        description: "",
        criteria: [{ id: 1, title: "C1", description: "", weight: 1, orderIndex: 0, levels: [] }],
      });
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="edit" rubricId={1} />);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument();
      });
    });

    it("submits update successfully", async () => {
      mockGetRubric.mockResolvedValueOnce({
        id: 1,
        title: "Test",
        description: "",
        criteria: [{ id: 1, title: "C1", description: "", weight: 1, orderIndex: 0, levels: [] }],
      });
      mockUpdateRubric.mockResolvedValueOnce({ id: 1 });
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="edit" rubricId={1} />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("Test")).toBeInTheDocument();
      });

      submitForm();

      await waitFor(() => {
        expect(mockUpdateRubric).toHaveBeenCalledWith(1, expect.any(Object));
      });
      expect(mockToastSuccess).toHaveBeenCalledWith("Rubric updated");
      expect(mockPush).toHaveBeenCalledWith("/dashboard/rubrics/1");
    });

    it("shows 409 conflict error on edit", async () => {
      mockGetRubric.mockResolvedValueOnce({
        id: 1,
        title: "Test",
        description: "",
        criteria: [{ id: 1, title: "C1", description: "", weight: 1, orderIndex: 0, levels: [] }],
      });
      mockUpdateRubric.mockRejectedValueOnce({ response: { status: 409, data: { detail: "conflict" } } });
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="edit" rubricId={1} />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("Test")).toBeInTheDocument();
      });

      submitForm();

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith(
          "This rubric is referenced by assignment templates and cannot be modified"
        );
      });
    });

    it("shows toast error and redirects on load failure", async () => {
      mockGetRubric.mockRejectedValueOnce(new Error("Not found"));
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="edit" rubricId={999} />);

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith("Failed to load rubric");
      });
      expect(mockPush).toHaveBeenCalledWith("/dashboard/rubrics");
    });

    it("cancel navigates to rubric detail in edit mode", async () => {
      mockGetRubric.mockResolvedValueOnce({
        id: 5,
        title: "Test",
        description: "",
        criteria: [{ id: 1, title: "C1", description: "", weight: 1, orderIndex: 0, levels: [] }],
      });
      const RubricBuilderForm = await loadComponent();
      const user = userEvent.setup();
      render(<RubricBuilderForm mode="edit" rubricId={5} />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("Test")).toBeInTheDocument();
      });

      await user.click(screen.getByRole("button", { name: /cancel/i }));
      expect(mockPush).toHaveBeenCalledWith("/dashboard/rubrics/5");
    });

    it("handles rubric with empty criteria array", async () => {
      mockGetRubric.mockResolvedValueOnce({
        id: 1,
        title: "Empty",
        description: "",
        criteria: [],
      });
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="edit" rubricId={1} />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("Empty")).toBeInTheDocument();
      });
      expect(screen.getByText("Criteria (1)")).toBeInTheDocument();
    });

    it("navigates to returnTo with rubricId on update", async () => {
      mockGetRubric.mockResolvedValueOnce({
        id: 1,
        title: "Test",
        description: "",
        criteria: [{ id: 1, title: "C1", description: "", weight: 1, orderIndex: 0, levels: [] }],
      });
      mockUpdateRubric.mockResolvedValueOnce({ id: 1 });
      const RubricBuilderForm = await loadComponent("returnTo=/dashboard/assignment-templates/edit");
      render(<RubricBuilderForm mode="edit" rubricId={1} />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("Test")).toBeInTheDocument();
      });

      submitForm();

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/dashboard/assignment-templates/edit?newRubricId=1");
      });
    });
  });

  describe("grid preview", () => {
    it("renders the live preview section", async () => {
      const RubricBuilderForm = await loadComponent();
      render(<RubricBuilderForm mode="create" />);
      expect(screen.getByText("Live Rubric Grid Preview")).toBeInTheDocument();
    });
  });
});
