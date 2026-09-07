import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, UserPlus, CheckSquare, FileText, Sun, Moon, ArrowRight, Building2 } from "lucide-react";
import { useTheme } from "next-themes";
import { useLeads } from "@/features/leads/hooks";
import { useTasks } from "@/features/tasks/hooks";
import { useCustomers } from "@/features/customers/hooks";
import { Dialog, DialogContent } from "@/components/ui/dialog";

export default function CommandPalette({ open, onOpenChange }) {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();

  const leadsQ = useLeads({ search: query.trim() || undefined, page_size: 5 });
  const tasksQ = useTasks({ search: query.trim() || undefined, page_size: 5 });
  const customersQ = useCustomers({ search: query.trim() || undefined, page_size: 5 });

  const leads = leadsQ.data?.results ?? leadsQ.data ?? [];
  const tasks = tasksQ.data?.results ?? tasksQ.data ?? [];
  const customers = customersQ.data?.results ?? customersQ.data ?? [];

  const handleSelect = (to) => {
    onOpenChange(false);
    setQuery("");
    navigate(to);
  };

  const quickActions = [
    { label: "Create new lead", icon: UserPlus, to: "/leads/new", badge: "Lead" },
    { label: "Create new task", icon: CheckSquare, to: "/tasks/new", badge: "Task" },
    { label: "Create quotation", icon: FileText, to: "/quotations/new", badge: "Quote" },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl w-[92vw] p-0 overflow-hidden border border-border/80 dark:border-emerald-500/30 bg-surface dark:bg-[#152520] rounded-[22px] shadow-2xl dark:shadow-[0_20px_60px_-15px_rgba(0,0,0,0.85),0_0_35px_rgba(28,99,87,0.35)] gap-0 [&>button:last-child]:hidden ring-1 ring-black/5 dark:ring-white/10">
        {/* Search Header */}
        <div className="flex items-center gap-3 px-4.5 py-4 border-b border-border bg-[var(--surface-sunken)] dark:bg-[#1A2E28]">
          <Search className="h-5 w-5 text-primary dark:text-[#52C4AC] shrink-0" />
          <input
            autoFocus
            placeholder="Type a command or search leads, customers, tasks…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-transparent border-none outline-none text-[15px] font-medium text-foreground placeholder:text-muted-foreground/80 font-sans pr-4"
          />
          <kbd className="inline-flex items-center px-2 py-0.5 text-[11px] font-mono font-bold text-muted-foreground dark:text-[#A4B8B0] bg-surface dark:bg-[#13201C] border border-border dark:border-white/10 rounded-md shrink-0 shadow-xs">
            ESC
          </kbd>
        </div>

        <div className="max-h-[390px] overflow-y-auto p-2.5 divide-y divide-border/60 dark:divide-white/10">
          {/* Quick Actions */}
          {!query && (
            <div className="p-2">
              <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground dark:text-[#8FA89E] mb-2 px-2">
                Quick Shortcuts
              </div>
              <div className="space-y-1">
                {quickActions.map((action) => (
                  <button
                    key={action.to}
                    onClick={() => handleSelect(action.to)}
                    className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium text-foreground hover:bg-primary-soft/80 dark:hover:bg-white/[0.08] hover:text-primary dark:hover:text-[#52C4AC] transition-all cursor-pointer text-left group"
                  >
                    <div className="flex items-center gap-3">
                      <action.icon className="h-4.5 w-4.5 text-primary dark:text-[#52C4AC] shrink-0 group-hover:scale-110 transition-transform" />
                      <span className="font-semibold">{action.label}</span>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-muted-foreground dark:text-[#B0C4BC] bg-muted dark:bg-white/10 px-2 py-0.5 rounded-md border border-transparent dark:border-white/5">
                      {action.badge}
                    </span>
                  </button>
                ))}
                <button
                  onClick={() => {
                    setTheme(theme === "dark" ? "light" : "dark");
                    onOpenChange(false);
                  }}
                  className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium text-foreground hover:bg-primary-soft/80 dark:hover:bg-white/[0.08] hover:text-primary dark:hover:text-[#52C4AC] transition-all cursor-pointer text-left group"
                >
                  <div className="flex items-center gap-3">
                    {theme === "dark" ? <Sun className="h-4.5 w-4.5 text-amber-400 group-hover:scale-110 transition-transform" /> : <Moon className="h-4.5 w-4.5 text-primary group-hover:scale-110 transition-transform" />}
                    <span className="font-semibold">Toggle Theme ({theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"})</span>
                  </div>
                  <span className="text-[10px] font-mono font-bold text-muted-foreground dark:text-[#B0C4BC] bg-muted dark:bg-white/10 px-2 py-0.5 rounded-md border border-transparent dark:border-white/5">Theme</span>
                </button>
              </div>
            </div>
          )}

          {/* Leads Results */}
          {leads.length > 0 && (
            <div className="p-2">
              <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground dark:text-[#8FA89E] mb-2 px-2">
                Leads ({leads.length})
              </div>
              <div className="space-y-1">
                {leads.map((lead) => (
                  <button
                    key={lead.id}
                    onClick={() => handleSelect(`/leads/${lead.id}`)}
                    className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs hover:bg-primary-soft/80 dark:hover:bg-white/[0.08] hover:text-primary dark:hover:text-[#52C4AC] transition-all cursor-pointer text-left group"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-7 h-7 rounded-lg bg-primary-soft dark:bg-primary/30 text-primary dark:text-[#52C4AC] font-display font-bold text-[11px] flex items-center justify-center shrink-0 border border-primary/20">
                        {(lead.name || "?").slice(0, 2).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <div className="font-semibold text-foreground truncate">{lead.name}</div>
                        <div className="text-[11px] text-muted-foreground truncate">{lead.company_name || lead.email || "Lead"}</div>
                      </div>
                    </div>
                    <span className="text-xs font-mono font-bold text-primary dark:text-[#52C4AC] shrink-0 ml-2">
                      {lead.total_value ? `₹${Number(lead.total_value).toLocaleString("en-IN")}` : "→"}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Customers Results */}
          {customers.length > 0 && (
            <div className="p-2">
              <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground dark:text-[#8FA89E] mb-2 px-2">
                Customers ({customers.length})
              </div>
              <div className="space-y-1">
                {customers.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => handleSelect(`/customers/${c.id}`)}
                    className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs hover:bg-primary-soft/80 dark:hover:bg-white/[0.08] hover:text-primary dark:hover:text-[#52C4AC] transition-all cursor-pointer text-left group"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-7 h-7 rounded-lg bg-primary-soft dark:bg-primary/30 text-primary dark:text-[#52C4AC] flex items-center justify-center shrink-0 border border-primary/20">
                        <Building2 className="h-4 w-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="font-semibold text-foreground truncate">{c.name}</div>
                        <div className="text-[11px] text-muted-foreground truncate">{c.company_name || c.email}</div>
                      </div>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground group-hover:text-primary dark:group-hover:text-[#52C4AC] group-hover:translate-x-0.5 transition-all" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Tasks Results */}
          {tasks.length > 0 && (
            <div className="p-2">
              <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground dark:text-[#8FA89E] mb-2 px-2">
                Tasks ({tasks.length})
              </div>
              <div className="space-y-1">
                {tasks.map((t) => (
                  <button
                    key={t.task_id}
                    onClick={() => handleSelect(t.lead ? `/leads/${t.lead}` : `/tasks/${t.task_id}`)}
                    className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs hover:bg-primary-soft/80 dark:hover:bg-white/[0.08] hover:text-primary dark:hover:text-[#52C4AC] transition-all cursor-pointer text-left group"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-7 h-7 rounded-lg bg-primary-soft dark:bg-primary/30 text-primary dark:text-[#52C4AC] flex items-center justify-center shrink-0 border border-primary/20">
                        <CheckSquare className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 font-semibold text-foreground truncate">{t.task_title}</div>
                    </div>
                    <span className="text-[11px] text-muted-foreground font-mono">
                      {t.due_date ? new Date(t.due_date).toLocaleDateString() : ""}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {query && !leads.length && !customers.length && !tasks.length && (
            <div className="py-10 text-center text-xs text-muted-foreground">
              No matching leads, customers, or tasks found for <strong className="text-foreground">"{query}"</strong>
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="px-4.5 py-2.5 border-t border-border bg-[var(--surface-sunken)] dark:bg-[#1A2E28] flex items-center justify-between text-[11px] text-muted-foreground dark:text-[#8FA89E] font-mono">
          <span>Navigate with mouse or keyboard</span>
          <span>DemoCRM Engine</span>
        </div>
      </DialogContent>
    </Dialog>
  );
}
