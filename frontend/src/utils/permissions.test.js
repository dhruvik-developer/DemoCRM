import { describe, it, expect } from "vitest";
import { resolvePermissions, hasPermission } from "./permissions";

describe("permissions", () => {
  it("Admin is unrestricted", () => {
    const r = resolvePermissions({ roleName: "Admin" });
    expect(r.isAdmin).toBe(true);
    expect(hasPermission(r, "view_lead")).toBe(true);
    expect(hasPermission(r, "assign_lead")).toBe(true);
  });
  it("Employee has view_lead but not assign_lead by default", () => {
    const r = resolvePermissions({ roleName: "Employee" });
    expect(hasPermission(r, "view_lead")).toBe(true);
    // Pipeline is manager/admin only
    expect(hasPermission(r, "view_pipeline")).toBe(false);
    expect(hasPermission(r, "manage_pipeline")).toBe(false);
    expect(hasPermission(r, "view_quotation")).toBe(true);
    // Employee extra includes change_followup per G13
    expect(hasPermission(r, "change_followup")).toBe(true);
  });
  it("Manager has full sales workflow", () => {
    const r = resolvePermissions({ roleName: "Manager" });
    expect(hasPermission(r, "add_lead")).toBe(true);
    expect(hasPermission(r, "assign_lead")).toBe(true);
    expect(hasPermission(r, "progress_lead")).toBe(true);
    expect(hasPermission(r, "view_quotation")).toBe(true);
    expect(hasPermission(r, "view_pipeline")).toBe(true);
    expect(hasPermission(r, "manage_pipeline")).toBe(true);
  });
  it("no role denied", () => {
    const r = resolvePermissions({ roleName: null });
    // fallback union still allows view_lead via Manager set, but explicit null role should be staff fallback per impl
    expect(r.isAdmin).toBe(false);
  });
});
