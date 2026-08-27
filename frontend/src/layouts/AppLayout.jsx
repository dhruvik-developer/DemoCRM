// Authenticated shell: permission-gated sidebar, topbar with notification
// bell slot + user menu (logout). Nav items are gated on the codenames from
// PERMISSION_CONTRACT.md; backend remains authoritative on 403s.

import { Link, NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bell,
  Building2,
  CalendarClock,
  CheckSquare,
  ChevronDown,
  ClipboardList,
  Database,
  FileText,
  GitBranch,
  LayoutDashboard,
  LogOut,
  Menu,
  PhoneCall,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useState } from "react";
import { Toaster } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent } from "@/components/ui/dialog";
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

const NAV_GROUPS = [
  {
    label: "CRM Sales",
    items: [
      { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
      { to: "/leads", label: "Leads", icon: Users, codename: "view_lead" },
      { to: "/tasks", label: "My Tasks", icon: CheckSquare, codename: "view_task" },
      { to: "/followups", label: "Activities", icon: PhoneCall, codename: "view_followup" },
      { to: "/admin/pipelines", label: "Pipeline", icon: GitBranch, codename: "view_pipeline" },
      { to: "/callforms", label: "Forms", icon: ClipboardList, codename: "manage_calltemplate" },
      { to: "/quotations", label: "Quotations", icon: FileText, codename: "view_quotation" },
      { to: "/customers", label: "Customers", icon: Building2, codename: "view_customer" },
    ],
  },
  {
    label: "Operations",
    items: [
      { to: "/meetings", label: "Meetings", icon: CalendarClock, codename: "view_meeting" },
      { to: "/followups", label: "Follow-ups", icon: PhoneCall, codename: "view_followup" },
      { to: "/reminders", label: "Reminders", icon: CalendarClock, codename: "view_reminder" },
      { to: "/notifications", label: "Notifications", icon: Bell, codename: "view_notificationtemplate" },
    ],
  },
  {
    label: "Administration",
    items: [
      { to: "/admin/roles", label: "Users / Roles", icon: ShieldCheck, codename: "view_role" },
      { to: "/admin/sources", label: "Lead Sources", icon: Database, codename: "view_leadsource" },
      { to: "/admin/pipelines", label: "Pipelines", icon: GitBranch, codename: "view_pipeline" },
      { to: "/callforms", label: "Form Templates", icon: ClipboardList, codename: "manage_calltemplate" },
      { to: "/notifications/templates", label: "Notification Templates", icon: Bell, codename: "view_notificationtemplate" },
    ],
  },
];
// eslint-disable-next-line no-unused-vars
const NAV_ITEMS = NAV_GROUPS.flatMap((g) => g.items);

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

function MobileNav({ open, onOpenChange, resolved }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="left-0 top-0 h-dvh w-72 translate-x-0 translate-y-0 p-0 max-w-none gap-0 rounded-none">
        <div className="flex h-14 items-center border-b px-4 text-lg font-semibold">CRM</div>
        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-2">
          {NAV_GROUPS.map((group) => {
            const visible = group.items.filter((i) => !i.codename || hasPermission(resolved, i.codename));
            if (!visible.length) return null;
            return (
              <div key={group.label} className="mb-2">
                <div className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{group.label}</div>
                <div className="flex flex-col gap-1">
                  {visible.map((item) => (
                    <NavLink key={`${group.label}-${item.to}`} to={item.to} end={item.end} onClick={() => onOpenChange(false)} className={({ isActive }) => ["flex items-center gap-3 rounded-md px-3 py-2 text-sm", isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"].join(" ")}>
                      <item.icon className="h-4 w-4" />
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>
      </DialogContent>
    </Dialog>
  );
}

export default function AppLayout() {
  const { user, resolved, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-background">
      <MobileNav open={mobileOpen} onOpenChange={setMobileOpen} resolved={resolved} />
      <aside className="hidden w-60 flex-col border-r bg-muted/30 md:flex">
        <div className="flex h-14 items-center border-b px-4 text-lg font-semibold tracking-tight">
          CRM
        </div>
        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-2">
          {NAV_GROUPS.map((group) => {
            const visible = group.items.filter((i) => !i.codename || hasPermission(resolved, i.codename));
            if (visible.length === 0) return null;
            return (
              <div key={group.label} className="mb-3">
                <div className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {group.label}
                </div>
                <div className="flex flex-col gap-1">
                  {visible.map((item) => (
                    <NavLink
                      key={`${group.label}-${item.to}`}
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
                  ))}
                </div>
              </div>
            );
          })}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b px-4">
          <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
            <Menu className="h-5 w-5" />
          </Button>
          <span className="hidden md:block" />
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
    </div>
  );
}
