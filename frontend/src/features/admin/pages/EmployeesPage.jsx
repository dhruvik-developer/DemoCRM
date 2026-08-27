import { useState, useMemo } from "react";
import { UserPlus, Search, Unlock } from "lucide-react";

import { useUsers, useUnlockUser } from "../hooks";
import AddEmployeeDialog from "../components/AddEmployeeDialog";
import { useAuth } from "@/hooks/useAuth";
import PageLoader from "@/components/common/PageLoader";
import PageError from "@/components/common/PageError";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function isAdminOrManager(user, resolved) {
  if (resolved?.isAdmin) return true;
  const roleName = user?.role_name ?? user?.role?.rolename;
  if (roleName === "Admin" || roleName === "Manager") return true;
  if (roleName === "Employee") return false;
  if (typeof user?.role === "number" && resolved?.codenames) {
    if (resolved.codenames.has("assign_task")) return true;
    return false;
  }
  return false;
}

export default function EmployeesPage() {
  const { user, resolved } = useAuth();
  const usersQuery = useUsers();
  const unlockUser = useUnlockUser();
  const [addOpen, setAddOpen] = useState(false);
  const [search, setSearch] = useState("");

  const canManage = isAdminOrManager(user, resolved);

  const filteredUsers = useMemo(() => {
    const list = usersQuery.data ?? [];
    if (!search.trim()) return list;
    const q = search.toLowerCase();
    return list.filter(
      (u) =>
        (u.username ?? "").toLowerCase().includes(q) ||
        (u.email ?? "").toLowerCase().includes(q) ||
        (u.full_name ?? "").toLowerCase().includes(q) ||
        (u.role ?? "").toLowerCase().includes(q)
    );
  }, [usersQuery.data, search]);

  if (!canManage) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <div className="max-w-md text-center">
          <h2 className="text-lg font-semibold">Access denied</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Only Admin and Manager can view and manage employees.
          </p>
        </div>
      </div>
    );
  }

  if (usersQuery.isLoading) {
    return <PageLoader label="Loading employees…" />;
  }

  if (usersQuery.isError) {
    return <PageError error={usersQuery.error} onRetry={usersQuery.refetch} />;
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Employees</h1>
          <p className="text-sm text-muted-foreground">
            View all employees and unlock blocked accounts. Only Admin and Manager can create employees.
          </p>
        </div>
        <Button onClick={() => setAddOpen(true)}>
          <UserPlus className="mr-2 h-4 w-4" />
          Add Employee
        </Button>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 pb-3">
          <CardTitle className="text-base">
            Employee list{" "}
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              ({filteredUsers.length})
            </span>
          </CardTitle>
          <div className="relative w-64">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by name, email, role…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8"
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Username</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                      No employees found.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredUsers.map((u) => (
                    <TableRow key={u.user_id}>
                      <TableCell className="font-medium">
                        {u.full_name || u.username}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{u.email}</TableCell>
                      <TableCell>{u.username}</TableCell>
                      <TableCell>
                        {u.role ? (
                          <Badge
                            variant={u.role === "Admin" ? "default" : u.role === "Manager" ? "secondary" : "outline"}
                          >
                            {u.role}
                          </Badge>
                        ) : (
                          <span className="text-sm text-muted-foreground">No Role</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={unlockUser.isPending}
                          onClick={() => unlockUser.mutate(u.user_id)}
                          title="Clear login rate-limit lock for this user"
                        >
                          <Unlock className="mr-1.5 h-3.5 w-3.5" />
                          Unlock
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <AddEmployeeDialog open={addOpen} onOpenChange={setAddOpen} />
    </div>
  );
}
