// Authenticated shell: permission-gated sidebar, topbar with notification
// bell slot + user menu (logout). Nav items are gated on the codenames from
// PERMISSION_CONTRACT.md; backend remains authoritative on 403s.

import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Users,
  Building2,
  CalendarClock,
  CheckSquare,
  ClipboardList,
  FileText,
  PhoneCall,
  LayoutDashboard,
  Bell,
  LogOut,
  ChevronDown,
  ShieldCheck,
  UserPlus,
} from "lucide-react";
import { Toaster } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";
import AddEmployeeDialog from "@/features/admin/components/AddEmployeeDialog";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  // Leads module is Admin-only under current role seeds (BACKEND_GAPS.md G23) —
  // gating keeps Employees/Managers out instead of serving them 403 pages.
  { to: "/leads", label: "Leads", icon: Users, codename: "view_lead" },
  { to: "/customers", label: "Customers", icon: Building2, codename: "view_customer" },
  { to: "/tasks", label: "Tasks", icon: CheckSquare, codename: "view_task" },
  { to: "/meetings", label: "Meetings", icon: CalendarClock, codename: "view_meeting" },
  { to: "/followups", label: "Follow-ups", icon: PhoneCall, codename: "view_followup" },
  { to: "/quotations", label: "Quotations", icon: FileText, codename: "view_quotation" },
  { to: "/callforms", label: "Call forms", icon: ClipboardList, codename: "view_calltemplate" },
  { to: "/notifications", label: "Notifications", icon: Bell, codename: "view_notificationtemplate" },
  { to: "/admin/roles", label: "Admin · Roles", icon: ShieldCheck, codename: "view_role" },
  { to: "/admin/roles", label: "Add Employee", icon: UserPlus, adminOnly: true, action: "addEmployee" },
];

function NotificationBell() {
  const { data } = useQuery({
    queryKey: ["notifications", "inbox", { is_read: "false", page_size: 1 }],
    queryFn: () =>
      apiClient
        .get(endpoints.notifications.list, {
          params: { is_read: "false", page_size: 1 },
        })
        .then((r) => r.data),
    refetchInterval: 30000,
    staleTime: 15000,
    retry: false,
  });
  const unread = data?.count ?? 0;

  return (
    <Button variant="ghost" size="icon" className="relative" asChild>
      <Link to="/notifications" aria-label="Notifications">
        <Bell className="h-5 w-5" />
        {unread > 0 ? (
          <Badge className="absolute -top-1 -right-1 h-4 min-w-4 rounded-full px-1 text-[10px] leading-4">
            {unread > 99 ? "99+" : unread}
          </Badge>
        ) : null}
      </Link>
    </Button>
  );
}

export default function AppLayout() {
  const { user, resolved, logout } = useAuth();
  const [addEmployeeOpen, setAddEmployeeOpen] = useState(false);

  const visibleNavItems = NAV_ITEMS.filter((item) => {
    if (item.adminOnly) return resolved?.isAdmin;
    return !item.codename || hasPermission(resolved, item.codename);
  });

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-60 flex-col border-r bg-muted/30 md:flex">
        <div className="flex h-14 items-center border-b px-4 text-lg font-semibold tracking-tight">
          CRM
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-2">
          {visibleNavItems.map((item) =>
            item.action === "addEmployee" ? (
              <button
                key={item.label}
                onClick={() => setAddEmployeeOpen(true)}
                className="flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </button>
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  [
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  ].join(" ")
                }
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            ),
          )}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b px-4">
          <span />
          <div className="flex items-center gap-1">
            <NotificationBell />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2">
                  <span className="max-w-40 truncate text-sm">
                    {user?.username ?? user?.email ?? "Account"}
                  </span>
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>
                  <span className="block max-w-52 truncate">{user?.email}</span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main className="flex min-w-0 flex-1 flex-col">
          <Outlet />
        </main>
      </div>

      <Toaster richColors position="top-right" />
      <AddEmployeeDialog open={addEmployeeOpen} onOpenChange={setAddEmployeeOpen} />
    </div>
  );
}
