// Roles admin: list, create (with permission picker), permission editing,
// delete, and the Assign-Role panel. Admin/Manager only server-side; the
// sidebar entry is gated on view_role.
// G6: no user-list endpoint exists, so role assignment takes a manual UUID.

import { useState } from "react";
import { useForm } from "react-hook-form";

import {
  useAssignRole,
  useCreateRole,
  useDeleteRole,
  usePermissions,
  useRoles,
  useUpdateRole,
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

const PROTECTED_ROLES = ["Admin", "Manager", "Employee"];

export default function AdminRolesPage() {
  const rolesQuery = useRoles();
  const permissionsQuery = usePermissions();
  const createRole = useCreateRole();
  const updateRole = useUpdateRole();
  const deleteRole = useDeleteRole();
  const assignRole = useAssignRole();

  const [createOpen, setCreateOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [assignUserId, setAssignUserId] = useState("");
  const [assignRoleId, setAssignRoleId] = useState("");

  const createForm = useForm({
    defaultValues: { rolename: "", description: "" },
  });
  const [editingPermissions, setEditingPermissions] = useState(null); // {role, selected:Set}

  if (rolesQuery.isLoading) return <PageLoader label="Loading roles…" />;
  if (rolesQuery.isError) {
    return <PageError error={rolesQuery.error} onRetry={rolesQuery.refetch} />;
  }

  const roles = rolesQuery.data ?? [];
  const permissions = permissionsQuery.data ?? [];
  const permissionName = (id) =>
    permissions.find((permission) => permission.id === id)?.codename ?? `#${id}`;

  // Derived safely so render never touches .selected on null (React Compiler
  // evaluates these during render, unlike the event handlers).
  const editingRoleId = editingPermissions?.role?.role_id ?? null;
  const editingRoleName = editingPermissions?.role?.rolename ?? "";
  const selectedPermissionIds = editingPermissions?.selected ?? new Set();

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Roles & permissions</h1>
        <Button onClick={() => setCreateOpen(true)}>New role</Button>
      </div>

      {/* Role cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {roles.map((role) => {
          const roleName = role?.rolename ?? "Unknown";
          const isProtected = PROTECTED_ROLES.includes(roleName);
          return (
            <Card key={role.role_id}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">{role.rolename}</CardTitle>
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
                <div className="flex flex-wrap gap-1">
                  {(role.permissions ?? []).slice(0, 8).map((id) => (
                    <Badge key={id} variant="outline" className="font-mono text-[10px]">
                      {permissionName(id)}
                    </Badge>
                  ))}
                  {(role.permissions ?? []).length > 8 ? (
                    <Badge variant="secondary">
                      +{(role.permissions ?? []).length - 8} more
                    </Badge>
                  ) : null}
                  {(role.permissions ?? []).length === 0 ? (
                    <span className="text-sm text-muted-foreground">No permissions.</span>
                  ) : null}
                </div>
                {!isProtected ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-fit"
                    onClick={() =>
                      setEditingPermissions({
                        role,
                        selected: new Set(role.permissions ?? []),
                      })
                    }
                  >
                    Edit permissions
                  </Button>
                ) : null}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Assign role — G6 workaround: manual UUID */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Assign role to user</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              assignRole
                .mutateAsync({ userId: assignUserId.trim(), roleId: Number(assignRoleId) })
                .then(() => {
                  setAssignUserId("");
                  setAssignRoleId("");
                });
            }}
          >
            <div className="min-w-64 flex-1">
              <FormField
                id="assign_user"
                label="User UUID"
                help="A searchable user list needs GET /users/ on the backend (BACKEND_GAPS.md G6)."
              >
                <Input
                  id="assign_user"
                  placeholder="00000000-0000-4000-8000-…"
                  value={assignUserId}
                  onChange={(event) => setAssignUserId(event.target.value)}
                />
              </FormField>
            </div>
            <div className="w-48">
              <FormField id="assign_role" label="Role">
                <select
                  id="assign_role"
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                  value={assignRoleId}
                  onChange={(event) => setAssignRoleId(event.target.value)}
                >
                  <option value="">Select…</option>
                  {roles.map((role) => (
                    <option key={role.role_id} value={role.role_id ?? ""}>
                      {role?.rolename ?? "Unnamed"}
                    </option>
                  ))}
                </select>
              </FormField>
            </div>
            <Button type="submit" disabled={!assignUserId.trim() || !assignRoleId || assignRole.isPending}>
              {assignRole.isPending ? "Assigning…" : "Assign"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New role</DialogTitle>
          </DialogHeader>
          <form onSubmit={createForm.handleSubmit((values) => createRole.mutateAsync(values).then(() => setCreateOpen(false)))} className="flex flex-col gap-3">
            <FormField id="new_role_name" label="Role name" error={createForm.formState.errors.rolename?.message}>
              <Input id="new_role_name" {...createForm.register("rolename")} />
            </FormField>
            <FormField id="new_role_description" label="Description">
              <Input id="new_role_description" {...createForm.register("description")} />
            </FormField>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={createRole.isPending}>Create</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit permissions dialog */}
      <Dialog
        open={Boolean(editingPermissions)}
        onOpenChange={(open) => !open && setEditingPermissions(null)}
      >
        <DialogContent className="max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Permissions — {editingRoleName}</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
            {permissions.map((permission) => {
              const checked = selectedPermissionIds.has(permission.id);
              return (
                <label key={permission.id} className="flex items-center gap-2 text-xs">
                  <input
                    type="checkbox"
                    className="h-3 w-3"
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
                  <span className="font-mono">{permission.codename}</span>
                </label>
              );
            })}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingPermissions(null)}>Cancel</Button>
            <Button
              disabled={updateRole.isPending}
              onClick={() =>
                updateRole
                  .mutateAsync({
                    roleId: editingRoleId,
                    // PATCH semantics: replaces the permission set.
                    permissions: [...selectedPermissionIds],
                  })
                  .then(() => setEditingPermissions(null))
              }
            >
              {updateRole.isPending ? "Saving…" : "Save"}
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
        onConfirm={() =>
          deleteRole.mutateAsync(pendingDelete.role_id).then(() => setPendingDelete(null))
        }
      />
    </div>
  );
}
