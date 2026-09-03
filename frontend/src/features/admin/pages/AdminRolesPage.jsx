import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";

import {
  useAssignRole,
  useCreateRole,
  useDeleteRole,
  usePermissions,
  useRoles,
  useUpdateRole,
  useUsers,
} from "../hooks";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import FormField from "@/components/forms/FormField";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const PROTECTED_ROLES = ["Admin", "Manager", "Employee"];

export default function AdminRolesPage() {
  const rolesQuery = useRoles();
  const permissionsQuery = usePermissions();
  const usersQuery = useUsers();
  const createRole = useCreateRole();
  const updateRole = useUpdateRole();
  const deleteRole = useDeleteRole();
  const assignRole = useAssignRole();

  const [createOpen, setCreateOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [assignUserId, setAssignUserId] = useState("");
  const [assignRoleId, setAssignRoleId] = useState("");

  const navigate = useNavigate();
  const createForm = useForm({
    defaultValues: { rolename: "", description: "" },
  });
  const [editingPermissions, setEditingPermissions] = useState(null); // {role, selected:Set}
  const [permSearch, setPermSearch] = useState("");
  const [expandedRoleId, setExpandedRoleId] = useState(null);

  if (rolesQuery.isLoading || permissionsQuery.isLoading) {
    return <PageLoader label="Loading roles & permissions…" />;
  }
  if (rolesQuery.isError) {
    return <PageError error={rolesQuery.error} onRetry={rolesQuery.refetch} />;
  }

  const roles = rolesQuery.data ?? [];
  const permissions = permissionsQuery.data ?? [];

  const getPermissionObj = (id) =>
    permissions.find((permission) => String(permission.id) === String(id));

  const editingRoleId = editingPermissions?.role?.role_id ?? null;
  const editingRoleName = editingPermissions?.role?.rolename ?? "";
  const selectedPermissionIds = editingPermissions?.selected ?? new Set();
  const dialogFiltered = permissions.filter((p) => {
    if (!permSearch.trim()) return true;
    const q = permSearch.toLowerCase().replace(/[_-]+/g, " ").trim();
    const nameNorm = (p.name || "").toLowerCase().replace(/[_-]+/g, " ");
    const codeNorm = (p.codename || "").toLowerCase().replace(/[_-]+/g, " ");
    return nameNorm.includes(q) || codeNorm.includes(q) || p.codename?.toLowerCase().includes(permSearch.toLowerCase()) || p.name?.toLowerCase().includes(permSearch.toLowerCase());
  });

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Roles & permissions</h1>
          <p className="text-sm text-muted-foreground">
            Manage roles, view permissions with details, and assign roles to employees.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>New role</Button>
      </div>

      {/* Role cards — Stitch: neutral border, subtle shadow, generous whitespace */}
      <div className="grid gap-4 md:grid-cols-2">
        {roles.map((role) => {
          const roleName = role?.rolename ?? "Unknown";
          const isProtected = PROTECTED_ROLES.includes(roleName);
          const assignedPerms = role.permissions ?? [];
          return (
            <Card key={role.role_id} className="rounded-[14px] border-outline-variant bg-white shadow-sm overflow-hidden">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base font-semibold">{role.rolename}</CardTitle>
                {!isProtected ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-destructive"
                    onClick={() => setPendingDelete(role)}
                  >
                    Delete
                  </Button>
                ) : (
                  <Badge variant="secondary">protected</Badge>
                )}
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {role.description ? (
                  <p className="text-sm text-muted-foreground">{role.description}</p>
                ) : null}
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-[#94A3B8] mb-1.5 block">
                    Assigned Permissions ({assignedPerms.length})
                  </span>
                  {(() => {
                    const isExpanded = expandedRoleId === role.role_id;
                    const displayPerms = isExpanded ? assignedPerms : assignedPerms.slice(0, 12);
                    return (
                      <>
                        <div className={`flex flex-wrap gap-1.5 pr-1 ${isExpanded ? "max-h-64 overflow-y-auto" : "max-h-36 overflow-y-auto"}`}>
                          {displayPerms.map((id) => {
                            const perm = getPermissionObj(id);
                            const label = perm?.name || perm?.codename || `#${id}`;
                            return (
                              <Badge
                                key={id}
                                variant="outline"
                                className="text-[11px] px-2 py-0.5 bg-white border-[#E2E8F0] font-medium"
                                title={perm ? `${perm.name} — ${perm.codename}` : `#${id}`}
                              >
                                {label}
                              </Badge>
                            );
                          })}
                          {!isExpanded && assignedPerms.length > 12 ? (
                            <Badge variant="secondary" className="text-[11px] bg-[#F1F5F9] text-[#475569]">+{assignedPerms.length - 12} more</Badge>
                          ) : null}
                          {assignedPerms.length === 0 ? (
                            <span className="text-sm text-muted-foreground">No permissions assigned.</span>
                          ) : null}
                        </div>
                        {assignedPerms.length > 12 && (
                          <button
                            type="button"
                            className="mt-1.5 text-xs font-semibold text-primary hover:underline"
                            onClick={() => setExpandedRoleId(isExpanded ? null : role.role_id)}
                          >
                            {isExpanded ? "Show less ↑" : `View all (${assignedPerms.length}) →`}
                          </button>
                        )}
                      </>
                    );
                  })()}
                </div>
                <Button
                  variant={isProtected ? "outline" : "outline"}
                  size="sm"
                  className={`w-fit mt-2 ${isProtected ? "border-amber-200 text-amber-700 hover:bg-amber-50" : ""}`}
                  onClick={() => navigate(`/admin/roles/${role.role_id}`)}
                >
                  {isProtected ? "Edit protected permissions" : "Manage permissions"}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Assign role to user */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Assign role to employee</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              if (!assignUserId || !assignRoleId) return;
              assignRole
                .mutateAsync({ userId: assignUserId, roleId: Number(assignRoleId) })
                .then(() => {
                  setAssignUserId("");
                  setAssignRoleId("");
                });
            }}
          >
            <div className="min-w-64 flex-1">
              <FormField id="assign_user" label="Select Employee">
                <Select value={assignUserId} onValueChange={setAssignUserId}>
                  <SelectTrigger id="assign_user">
                    <SelectValue placeholder="Select Employee…" />
                  </SelectTrigger>
                  <SelectContent>
                    {(usersQuery.data ?? []).map((u) => (
                      <SelectItem key={u.user_id} value={u.user_id}>
                        {u.full_name || u.username} {u.role ? `(${u.role})` : "(No Role)"}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
            </div>
            <div className="w-56">
              <FormField id="assign_role" label="Target Role">
                <select
                  id="assign_role"
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                  value={assignRoleId}
                  onChange={(event) => setAssignRoleId(event.target.value)}
                >
                  <option value="">Select Role…</option>
                  {roles.map((role) => (
                    <option key={role.role_id} value={role.role_id ?? ""}>
                      {role?.rolename ?? "Unnamed"}
                    </option>
                  ))}
                </select>
              </FormField>
            </div>
            <Button type="submit" disabled={!assignUserId || !assignRoleId || assignRole.isPending}>
              {assignRole.isPending ? "Assigning…" : "Assign role"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Create role dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New role</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={createForm.handleSubmit((values) =>
              createRole.mutateAsync(values).then(() => setCreateOpen(false)),
            )}
            className="flex flex-col gap-3"
          >
            <FormField
              id="new_role_name"
              label="Role name"
              error={createForm.formState.errors.rolename?.message}
            >
              <Input id="new_role_name" placeholder="e.g. Lead Manager" {...createForm.register("rolename")} />
            </FormField>
            <FormField id="new_role_description" label="Description">
              <Input
                id="new_role_description"
                placeholder="Allows managing leads and assigning team members"
                {...createForm.register("description")}
              />
            </FormField>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createRole.isPending}>
                Create
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit permissions dialog */}
      <Dialog
        open={Boolean(editingPermissions)}
        onOpenChange={(open) => {
          if (!open) {
            setEditingPermissions(null);
            setPermSearch("");
          }
        }}
      >
        <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Permissions — {editingRoleName}</DialogTitle>
          </DialogHeader>
          <p className="text-xs text-muted-foreground">
            Check permissions to assign them to this role. Permission names and codenames are loaded directly from the system backend. Search to filter (e.g. “delete_quotation”, “view_lead”).
          </p>
          <Input placeholder="Search permissions by name or codename..." value={permSearch} onChange={(e) => setPermSearch(e.target.value)} className="mt-2" />
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 mt-2 max-h-[50vh] overflow-y-auto pr-1">
            {dialogFiltered.length === 0 ? (
              <div className="col-span-2 py-8 text-center text-sm text-muted-foreground">
                No permissions match “{permSearch}”. Try “delete_quotation” or “view lead”.
              </div>
            ) : (
              dialogFiltered.map((permission) => {
                const checked = selectedPermissionIds.has(permission.id);
              return (
                <label
                  key={permission.id}
                  className={`flex items-start gap-2.5 rounded-md border p-2.5 text-xs transition-colors cursor-pointer ${
                    checked
                      ? "border-primary/50 bg-primary/5"
                      : "hover:bg-muted/40"
                  }`}
                >
                  <input
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    checked={Boolean(checked)}
                    onChange={(event) => {
                      setEditingPermissions((previous) => {
                        if (!previous) return previous;
                        const selected = new Set(previous.selected);
                        if (event.target.checked) {
                          selected.add(permission.id);
                        } else {
                          selected.delete(permission.id);
                        }
                        return { ...previous, selected };
                      });
                    }}
                  />
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <span className="font-semibold text-foreground text-xs leading-tight">
                      {permission.name || permission.codename}
                    </span>
                    <span className="font-mono text-[11px] text-muted-foreground truncate">
                      {permission.codename}
                    </span>
                  </div>
                </label>
              );
              })
            )}
          </div>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setEditingPermissions(null)}>
              Cancel
            </Button>
            <Button
              disabled={updateRole.isPending}
              onClick={() =>
                updateRole
                  .mutateAsync({
                    roleId: editingRoleId,
                    permissions: [...selectedPermissionIds],
                  })
                  .then(() => setEditingPermissions(null))
              }
            >
              {updateRole.isPending ? "Saving…" : "Save permissions"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title={`Delete role "${pendingDelete?.rolename}"?`}
        description="Users holding this role will lose their permissions."
        confirmLabel="Delete"
        destructive
        loading={deleteRole.isPending}
        onConfirm={() => {
          if (pendingDelete == null) return;
          deleteRole.mutateAsync(pendingDelete.role_id).then(() => setPendingDelete(null));
        }}
      />
    </div>
  );
}
