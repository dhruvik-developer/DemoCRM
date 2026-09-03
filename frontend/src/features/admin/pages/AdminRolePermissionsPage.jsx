import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { usePermissions, useRoles, useUpdateRole } from "../hooks";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

function getGroup(permission) {
  const code = permission.codename || "";
  const parts = code.split("_");
  if (parts.length <= 1) return "general";
  return parts.slice(1).join("_");
}

function formatGroupTitle(group) {
  if (group === "general") return "General";
  return group
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function AdminRolePermissionsPage() {
  const { roleId } = useParams();
  const navigate = useNavigate();
  const rolesQuery = useRoles();
  const permissionsQuery = usePermissions();
  const updateRole = useUpdateRole();

  const [search, setSearch] = useState("");
  const [localSelected, setLocalSelected] = useState(null);

  const roles = useMemo(() => rolesQuery.data ?? [], [rolesQuery.data]);
  const permissions = useMemo(() => permissionsQuery.data ?? [], [permissionsQuery.data]);
  const role = roles.find((r) => String(r.role_id) === String(roleId));

  const selected = useMemo(() => new Set(role?.permissions ?? []), [role]);

  const grouped = useMemo(() => {
    const map = new Map();
    permissions.forEach((p) => {
      const g = getGroup(p);
      if (!map.has(g)) map.set(g, []);
      map.get(g).push(p);
    });
    for (const v of map.values()) {
      v.sort((a, b) => (a.name || a.codename).localeCompare(b.name || b.codename));
    }
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [permissions]);

  const filteredGrouped = useMemo(() => {
    if (!search.trim()) return grouped;
    const q = search.toLowerCase().replace(/[_-]+/g, " ").trim();
    return grouped
      .map(([group, perms]) => {
        const filtered = perms.filter((p) => {
          const nameNorm = (p.name || "").toLowerCase().replace(/[_-]+/g, " ");
          const codeNorm = (p.codename || "").toLowerCase().replace(/[_-]+/g, " ");
          return (
            nameNorm.includes(q) ||
            codeNorm.includes(q) ||
            p.codename?.toLowerCase().includes(search.toLowerCase()) ||
            p.name?.toLowerCase().includes(search.toLowerCase())
          );
        });
        return [group, filtered];
      })
      .filter(([, perms]) => perms.length > 0);
  }, [grouped, search]);

  const activeSelected = localSelected ?? selected;
  const isDirty = localSelected ? JSON.stringify([...localSelected].sort()) !== JSON.stringify([...selected].sort()) : false;

  const handleToggle = (permId) => {
    setLocalSelected((prev) => {
      const base = prev ?? new Set(role?.permissions ?? []);
      const next = new Set(base);
      if (next.has(permId)) next.delete(permId);
      else next.add(permId);
      return next;
    });
  };

  const handleGroupToggle = (groupPerms, checked) => {
    setLocalSelected((prev) => {
      const base = prev ?? new Set(role?.permissions ?? []);
      const next = new Set(base);
      groupPerms.forEach((p) => {
        if (checked) next.add(p.id);
        else next.delete(p.id);
      });
      return next;
    });
  };

  if (rolesQuery.isLoading || permissionsQuery.isLoading) {
    return <PageLoader label="Loading role permissions…" />;
  }
  if (rolesQuery.isError) {
    return <PageError error={rolesQuery.error} onRetry={rolesQuery.refetch} />;
  }
  if (!role) {
    return (
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
        <p className="text-sm text-muted-foreground">Role not found.</p>
        <Button variant="outline" asChild className="w-fit">
          <Link to="/admin/roles">Back to roles</Link>
        </Button>
      </div>
    );
  }

  const handleSave = async () => {
    const perms = [...(localSelected ?? selected)];
    await updateRole.mutateAsync({ roleId: role.role_id, permissions: perms });
    navigate("/admin/roles");
  };

  const handleReset = () => setLocalSelected(new Set(role.permissions ?? []));

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs text-muted-foreground">
            <Link to="/admin/roles" className="hover:underline">
              Roles & permissions
            </Link>{" "}
            / <span className="font-medium text-foreground">{role.rolename}</span>
          </div>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            Permissions — {role.rolename}
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            All permissions are grouped by module. Check to assign to this role. Changes are per role and affect every employee holding it. {["Admin", "Manager", "Employee"].includes(role.rolename) ? "This is a protected role — edit carefully." : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link to="/admin/roles">Back</Link>
          </Button>
          <Button onClick={handleSave} disabled={!isDirty || updateRole.isPending}>
            {updateRole.isPending ? "Saving…" : "Save permissions"}
          </Button>
        </div>
      </div>

      <Card className="rounded-[14px] border-[#E5E7EB] bg-white shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-sm font-semibold">
              {role.rolename} — {activeSelected.size} permissions assigned
            </CardTitle>
            <Badge variant="secondary" className="text-[11px]">
              {permissions.length} total
            </Badge>
          </div>
          {role.description ? <p className="text-xs text-muted-foreground">{role.description}</p> : null}
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Input
            placeholder="Search permissions by name or codename — e.g. delete_quotation, view lead, manage pipeline"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              Showing {filteredGrouped.reduce((acc, [, perms]) => acc + perms.length, 0)} of {permissions.length} permissions
            </span>
            <div className="flex gap-1.5">
              <Button variant="outline" size="sm" className="h-7 text-xs" onClick={handleReset} disabled={!isDirty}>
                Reset
              </Button>
              <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setLocalSelected(new Set(permissions.map((p) => p.id)))}>
                Select all
              </Button>
              <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setLocalSelected(new Set())}>
                Clear
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {filteredGrouped.map(([group, perms]) => {
        const groupTitle = formatGroupTitle(group);
        const allChecked = perms.every((p) => activeSelected.has(p.id));
        const someChecked = perms.some((p) => activeSelected.has(p.id));
        return (
          <Card key={group} className="rounded-[14px] border-[#E5E7EB] bg-white shadow-sm overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between gap-2 bg-[#F9FAFB] border-b border-[#E5E7EB] py-3">
              <div>
                <CardTitle className="text-sm font-semibold capitalize">{groupTitle}</CardTitle>
                <p className="text-xs text-muted-foreground">{perms.length} permissions</p>
              </div>
              <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                  checked={allChecked}
                  ref={(el) => {
                    if (el) el.indeterminate = !allChecked && someChecked;
                  }}
                  onChange={(e) => handleGroupToggle(perms, e.target.checked)}
                />
                Select all
              </label>
            </CardHeader>
            <CardContent className="p-3">
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {perms.map((permission) => {
                  const checked = activeSelected.has(permission.id);
                  return (
                    <label
                      key={permission.id}
                      className={`flex items-start gap-2.5 rounded-lg border p-3 text-xs transition-colors cursor-pointer ${
                        checked ? "border-[#C7D2FE] bg-[#EEF2FF]" : "border-[#E5E7EB] hover:bg-[#F9FAFB]"
                      }`}
                    >
                      <input
                        type="checkbox"
                        className="mt-0.5 h-4 w-4 rounded border-gray-300 text-[#4F46E5] focus:ring-[#4F46E5]"
                        checked={checked}
                        onChange={() => handleToggle(permission.id)}
                      />
                      <div className="min-w-0 flex flex-col gap-0.5">
                        <span className="font-semibold leading-tight text-[#0F172A] line-clamp-2">{permission.name || permission.codename}</span>
                        <span className="font-mono text-[11px] text-[#64748B] truncate">{permission.codename}</span>
                        <span className="text-[10px] text-[#94A3B8]">ID #{permission.id}</span>
                      </div>
                    </label>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        );
      })}

      {filteredGrouped.length === 0 ? (
        <Card className="rounded-[14px] border-dashed p-8 text-center text-sm text-muted-foreground">
          No permissions match “{search}”. Try “delete_quotation” or “view lead”.
        </Card>
      ) : null}

      <Separator />

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={() => navigate("/admin/roles")}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={!isDirty || updateRole.isPending} className="bg-[#4F46E5] hover:bg-[#4338CA]">
          {updateRole.isPending ? "Saving…" : `Save ${activeSelected.size} permissions`}
        </Button>
      </div>
    </div>
  );
}
