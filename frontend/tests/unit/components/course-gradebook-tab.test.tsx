import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import CourseGradebookTab from "@/components/courses/CourseGradebookTab";

describe("CourseGradebookTab", () => {
  it("renders placeholder message", () => {
    render(<CourseGradebookTab courseId={1} />);
    expect(
      screen.getByText("Gradebook for this course will appear here."),
    ).toBeInTheDocument();
  });

  it("renders with border card styling", () => {
    const { container } = render(<CourseGradebookTab courseId={42} />);
    const card = container.firstElementChild;
    expect(card).toHaveClass("rounded-sm");
    expect(card).toHaveClass("border");
  });
});
