import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { useWorkflowCapabilities } from "./useWorkflowCapabilities";
import { resolvePermissions } from "@/utils/permissions";

describe("useWorkflowCapabilities", () => {
  const perms = resolvePermissions({ roleName: "Manager" });
  const stages = [
    { id: "s1", display_order: 1, requires_quotation: false },
    { id: "s2", display_order: 2, requires_quotation: true },
    { id: "s3", display_order: 3 },
  ];
  it("derives canProgress true when active and not final", () => {
    const { result } = renderHook(() => useWorkflowCapabilities({ lead: { status: "ACTIVE", current_stage: "s1" }, stages, currentStage: stages[0], currentForm: { fields: [{ field_key: "a" }] }, permissions: perms, quotation: null }));
    expect(result.current.canProgress).toBe(true);
    expect(result.current.requiresQuotation).toBe(false);
  });
  it("requiresQuotation blocks convert until accepted", () => {
    const { result } = renderHook(() => useWorkflowCapabilities({ lead: { status: "ACTIVE", current_stage: "s2" }, stages, currentStage: stages[1], currentForm: null, permissions: perms, quotation: { status: "DRAFT" } }));
    expect(result.current.requiresQuotation).toBe(true);
    expect(result.current.canConvert).toBe(false);
  });
  it("allows convert when quotation accepted", () => {
    const { result } = renderHook(() => useWorkflowCapabilities({ lead: { status: "ACTIVE", current_stage: "s2" }, stages, currentStage: stages[1], currentForm: null, permissions: perms, quotation: { status: "ACCEPTED" } }));
    expect(result.current.canConvert).toBe(true);
  });
});
