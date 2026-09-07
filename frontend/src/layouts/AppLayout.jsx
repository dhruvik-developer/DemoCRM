// Authenticated shell: permission-gated sidebar, topbar with notification
// bell slot + user menu (logout). Nav items are gated on the codenames from
// PERMISSION_CONTRACT.md; backend remains authoritative on 403s.

import { Link, NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bell,
  Building2,
  CalendarDays,
  CalendarClock,
  CheckSquare,
  ChevronDown,
  ClipboardList,
  Database,
  FileText,
  GitBranch,
  Layers,
  LayoutDashboard,
  LogOut,
  Menu,
  PhoneCall,
  Search,
  Settings,
  ShieldCheck,
  Users,
  Sun,
  Moon,
} from "lucide-react";
import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import CommandPalette from "@/components/common/CommandPalette";
import Breadcrumbs from "@/components/common/Breadcrumbs";
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
      { to: "/calendar", label: "Calendar", icon: CalendarDays, codename: "view_task" },
      { to: "/meetings", label: "Meetings", icon: CalendarClock, codename: "view_meeting" },
      { to: "/followups", label: "Follow-ups", icon: PhoneCall, codename: "view_followup" },
      { to: "/notifications", label: "Notifications", icon: Bell, codename: "view_notificationtemplate", end: true },
    ],
  },
  {
    label: "Administration",
    items: [
      { to: "/admin/roles", label: "Users / Roles", icon: ShieldCheck, codename: "view_role" },
      { to: "/admin/sources", label: "Lead Sources", icon: Database, codename: "manage_lead_source" },
      { to: "/admin/pipelines", label: "Pipelines", icon: GitBranch, codename: "manage_pipeline" },
      { to: "/callforms", label: "Form Templates", icon: ClipboardList, codename: "manage_calltemplate" },
      { to: "/admin/audit-logs", label: "Audit Logs", icon: Database, codename: "view_auditlog" },
    ],
  },
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
    <Button variant="ghost" size="icon" className="relative rounded-full text-foreground/80 hover:bg-muted" asChild>
      <Link to="/notifications" aria-label="Notifications">
        <Bell className="h-[18px] w-[18px]" />
        {unread > 0 ? (
          <Badge className="absolute -top-0.5 -right-0.5 h-4 min-w-4 rounded-full bg-secondary px-1 text-[10px] font-mono font-bold text-[#2B1206]">
            {unread > 99 ? "99+" : unread}
          </Badge>
        ) : null}
      </Link>
    </Button>
  );
}

function MobileNav({ open, onOpenChange, resolved, user, logout }) {
  const initials = (user?.username || user?.email || "U").slice(0, 2).toUpperCase();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="left-0 top-0 h-dvh w-[264px] translate-x-0 translate-y-0 p-0 max-w-none gap-0 rounded-none bg-[#113D37] text-[#DCEAE4] border-r border-white/10 flex flex-col">
        <div className="flex items-center gap-[11px] px-[22px] py-5 shrink-0 border-b border-white/10">
          <div className="h-[34px] w-[34px] rounded-[10px] bg-[#FF6A3D] flex items-center justify-center shrink-0 shadow-sm">
            <Layers className="h-[18px] w-[18px] text-[#2B1206] stroke-[2.2]" />
          </div>
          <div>
            <div className="font-display text-[17px] font-semibold text-white leading-tight">DemoCRM</div>
            <div className="text-[10.5px] text-[#9FC1B6] tracking-wide mt-0.5">Sales Engine v2.4</div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3.5 py-2">
          {NAV_GROUPS.map((group) => {
            const visible = group.items.filter((i) => !i.codename || hasPermission(resolved, i.codename));
            if (!visible.length) return null;
            return (
              <div key={group.label} className="mb-3">
                <div className="px-3 pt-3 pb-1.5 text-[11px] font-semibold uppercase tracking-[.02em] text-[#7FA79A]">
                  {group.label}
                </div>
                <div className="flex flex-col gap-0.5">
                  {visible.map((item) => (
                    <NavLink
                      key={`${group.label}-${item.to}`}
                      to={item.to}
                      end={item.end}
                      onClick={() => onOpenChange(false)}
                      className={({ isActive }) =>
                        [
                          "relative flex items-center gap-[11px] px-3 py-[9px] rounded-[9px] text-[13px] font-medium transition-colors",
                          isActive
                            ? "bg-white/[0.12] text-white font-semibold before:content-[''] before:absolute before:-left-3.5 before:top-2 before:bottom-2 before:w-[3px] before:rounded-r-[4px] before:bg-[#FF6A3D]"
                            : "text-[#CFE3DB] hover:bg-white/[0.07] hover:text-white",
                        ].join(" ")
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <item.icon className={`h-[18px] w-[18px] shrink-0 ${isActive ? "text-[#FF9770]" : "text-[#8FB6A9]"}`} />
                          <span className="flex-1 truncate">{item.label}</span>
                        </>
                      )}
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>

        <div className="p-4 border-t border-white/10 flex items-center gap-2.5 shrink-0 bg-[#0A2B26]/40">
          <div className="w-[34px] h-[34px] rounded-full bg-[#DDECE5] text-[#0A2B26] font-display font-bold text-xs flex items-center justify-center shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[12.5px] font-semibold text-white truncate">{user?.username || user?.email?.split("@")[0] || "User"}</div>
            <div className="text-[10.5px] text-[#8FB6A9] truncate">{user?.role || "Staff"}</div>
          </div>
          <Button variant="ghost" size="sm" onClick={logout} className="text-white/70 hover:text-white hover:bg-white/10 p-1.5 h-auto">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

import FloatingActionButton from "@/components/common/FloatingActionButton";

export default function AppLayout() {
  const { user, resolved, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const initials = (user?.username || user?.email || "U").slice(0, 2).toUpperCase();

  // Keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    const down = (e) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setCommandOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <MobileNav open={mobileOpen} onOpenChange={setMobileOpen} resolved={resolved} user={user} logout={logout} />
      <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />

      {/* Desktop Sidebar — 264px Meridian Pine */}
      <aside className="hidden h-screen w-[264px] shrink-0 flex-col bg-[#113D37] text-[#DCEAE4] md:flex sticky top-0 z-30 shadow-sm">
        <div className="flex items-center gap-[11px] px-[22px] py-5 shrink-0">
          <div className="h-[34px] w-[34px] rounded-[10px] bg-[#FF6A3D] flex items-center justify-center shrink-0 shadow-sm">
            <Layers className="h-[18px] w-[18px] text-[#2B1206] stroke-[2.2]" />
          </div>
          <div>
            <div className="font-display text-[17px] font-semibold text-white leading-tight">DemoCRM</div>
            <div className="text-[10.5px] text-[#9FC1B6] tracking-wide mt-0.5">Sales Engine v2.4</div>
          </div>
        </div>

        <nav className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-3.5 py-2">
          {NAV_GROUPS.map((group) => {
            const visible = group.items.filter((i) => !i.codename || hasPermission(resolved, i.codename));
            if (visible.length === 0) return null;
            return (
              <div key={group.label} className="mb-2.5">
                <div className="px-3 pt-3 pb-1.5 text-[11px] font-semibold uppercase tracking-[.02em] text-[#7FA79A]">
                  {group.label}
                </div>
                <div className="flex flex-col gap-0.5">
                  {visible.map((item) => (
                    <NavLink
                      key={`${group.label}-${item.to}`}
                      to={item.to}
                      end={item.end}
                      className={({ isActive }) =>
                        [
                          "relative flex items-center gap-[11px] px-3 py-[9px] rounded-[9px] text-[13px] font-medium transition-colors",
                          isActive
                            ? "bg-white/[0.12] text-white font-semibold before:content-[''] before:absolute before:-left-3.5 before:top-2 before:bottom-2 before:w-[3px] before:rounded-r-[4px] before:bg-[#FF6A3D]"
                            : "text-[#CFE3DB] hover:bg-white/[0.07] hover:text-white",
                        ].join(" ")
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <item.icon className={`h-[18px] w-[18px] shrink-0 ${isActive ? "text-[#FF9770]" : "text-[#8FB6A9]"}`} />
                          <span className="flex-1 truncate">{item.label}</span>
                        </>
                      )}
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}

          <div className="mt-auto border-t border-white/10 pt-2 pb-1">
            <NavLink
              to="/settings"
              className={({ isActive }) =>
                [
                  "relative flex items-center gap-[11px] px-3 py-[9px] rounded-[9px] text-[13px] font-medium transition-colors",
                  isActive
                    ? "bg-white/[0.12] text-white font-semibold before:content-[''] before:absolute before:-left-3.5 before:top-2 before:bottom-2 before:w-[3px] before:rounded-r-[4px] before:bg-[#FF6A3D]"
                    : "text-[#CFE3DB] hover:bg-white/[0.07] hover:text-white",
                ].join(" ")
              }
            >
              {({ isActive }) => (
                <>
                  <Settings className={`h-[18px] w-[18px] shrink-0 ${isActive ? "text-[#FF9770]" : "text-[#8FB6A9]"}`} />
                  <span className="flex-1 truncate">Settings</span>
                  {user?.must_change_password ? (
                    <span className="rounded-full bg-[#FF6A3D] px-1.5 py-0.5 text-[10px] font-mono font-bold text-[#2B1206]">action</span>
                  ) : null}
                </>
              )}
            </NavLink>
          </div>
        </nav>

        {/* User Profile Footer */}
        <div className="p-3.5 border-t border-white/10 flex items-center gap-2.5 shrink-0 bg-[#0A2B26]/40">
          <div className="w-[34px] h-[34px] rounded-full bg-[#DDECE5] text-[#0A2B26] font-display font-bold text-xs flex items-center justify-center shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[12.5px] font-semibold text-white truncate">{user?.username || user?.email?.split("@")[0] || "User"}</div>
            <div className="text-[10.5px] text-[#8FB6A9] truncate">{user?.role || "Team Member"}</div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-white/70 hover:text-white hover:bg-white/10">
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel>
                <span className="block truncate text-xs text-muted-foreground">{user?.email}</span>
              </DropdownMenuLabel>
              <DropdownMenuItem asChild>
                <Link to="/settings" className="cursor-pointer">
                  <Settings className="mr-2 h-4 w-4" /> Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout} className="cursor-pointer text-destructive focus:text-destructive">
                <LogOut className="mr-2 h-4 w-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden bg-background">
        {/* Topbar — 64px sticky */}
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-surface px-6 sticky top-0 z-20 shadow-sm">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
              <Menu className="h-5 w-5" />
            </Button>
            <Breadcrumbs />
          </div>

          <div className="flex items-center gap-3">
            {/* Global Quick Command Palette Trigger */}
            <button
              onClick={() => setCommandOpen(true)}
              className="hidden sm:flex items-center justify-between gap-3 bg-[var(--surface-sunken)] border border-border rounded-full px-3.5 py-1.5 w-60 lg:w-72 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground transition-all cursor-pointer shadow-xs"
            >
              <div className="flex items-center gap-2 truncate">
                <Search className="h-3.5 w-3.5 text-primary shrink-0" />
                <span className="truncate">Quick search or command…</span>
              </div>
              <kbd className="hidden lg:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-mono font-bold text-muted-foreground bg-surface border border-border rounded shadow-xs">
                ⌘K
              </kbd>
            </button>

            {/* Theme Toggle Button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-full text-foreground hover:bg-muted"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              title="Toggle theme (Light / Dark)"
            >
              {theme === "dark" ? (
                <Sun className="h-4 w-4 text-amber-400" />
              ) : (
                <Moon className="h-4 w-4 text-primary" />
              )}
            </Button>

            <NotificationBell />

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2 rounded-full pl-2 pr-3 hover:bg-muted">
                  <div className="w-7 h-7 rounded-full bg-primary text-white font-display font-bold text-xs flex items-center justify-center">
                    {initials}
                  </div>
                  <span className="max-w-32 truncate text-xs font-semibold text-foreground hidden sm:inline">
                    {user?.username || user?.email?.split("@")[0] || "Account"}
                  </span>
                  <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52">
                <DropdownMenuLabel>
                  <span className="block font-medium truncate">{user?.username}</span>
                  <span className="block text-xs font-normal text-muted-foreground truncate">{user?.email}</span>
                </DropdownMenuLabel>
                <DropdownMenuItem asChild>
                  <Link to="/settings"><Settings className="mr-2 h-4 w-4" /> Settings</Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} className="text-destructive focus:text-destructive cursor-pointer">
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto bg-background">
          <Outlet />
        </main>
      </div>

      <FloatingActionButton onOpenCommand={() => setCommandOpen(true)} />
      <Toaster richColors position="top-right" />
    </div>
  );
}
