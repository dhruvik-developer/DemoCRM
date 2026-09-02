import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PipelineStepper from "./PipelineStepper";

describe("PipelineStepper", () => {
  it("renders stages and marks active", () => {
    const stages = [{ id: "1", name: "Lead", display_order: 1 }, { id: "2", name: "Proposal", display_order: 2, requires_quotation: true }];
    render(<PipelineStepper stages={stages} currentStageId="1" />);
    expect(screen.getByText("Lead")).toBeInTheDocument();
    expect(screen.getByText("Proposal")).toBeInTheDocument();
    expect(screen.getByText("Quotation")).toBeInTheDocument();
  });
});
