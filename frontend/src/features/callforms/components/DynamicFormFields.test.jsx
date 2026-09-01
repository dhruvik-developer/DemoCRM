import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import DynamicFormFields from "./DynamicFormFields";

describe("DynamicFormFields", () => {
  it("renders required marker", () => {
    const fields = [{ id: "1", field_key: "phone", label: "Phone", field_type: "text", is_required: true }];
    render(<DynamicFormFields fields={fields} values={{}} errors={{}} onChange={() => {}} />);
    expect(screen.getByText(/Phone/)).toBeInTheDocument();
    expect(document.body.innerHTML).toContain("*");
  });
});
