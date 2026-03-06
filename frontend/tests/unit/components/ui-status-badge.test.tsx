import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/ui/status-badge";

describe("StatusBadge", () => {
  it("renders ACTIVE status with correct label", () => {
    render(<StatusBadge status="ACTIVE" />);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders ARCHIVED status with correct label", () => {
    render(<StatusBadge status="ARCHIVED" />);
    expect(screen.getByText("Archived")).toBeInTheDocument();
  });

  it("renders DRAFT status with correct label", () => {
    render(<StatusBadge status="DRAFT" />);
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("renders SEALED status as Ready", () => {
    render(<StatusBadge status="SEALED" />);
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("renders LIVE status with correct label", () => {
    render(<StatusBadge status="LIVE" />);
    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("renders SNAPSHOT status with correct label", () => {
    render(<StatusBadge status="SNAPSHOT" />);
    expect(screen.getByText("Snapshot")).toBeInTheDocument();
  });

  it("renders unknown status as-is using draft variant", () => {
    render(<StatusBadge status="UNKNOWN_STATUS" />);
    expect(screen.getByText("UNKNOWN_STATUS")).toBeInTheDocument();
  });

  it("uses custom label when provided", () => {
    render(<StatusBadge status="ACTIVE" label="Custom Label" />);
    expect(screen.getByText("Custom Label")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<StatusBadge status="ACTIVE" className="extra" />);
    const badge = container.querySelector("span");
    expect(badge).toHaveClass("extra");
  });

  it("renders as an inline-flex span", () => {
    const { container } = render(<StatusBadge status="DRAFT" />);
    const badge = container.querySelector("span");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("inline-flex");
  });
});
