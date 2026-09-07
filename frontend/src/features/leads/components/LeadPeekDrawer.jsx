import { Link } from "react-router-dom";
import { X, Building2, Mail, Phone, ExternalLink, Layers, Calendar } from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import StatusBadge from "@/components/common/StatusBadge";
import { useMasterDataMaps } from "@/features/crm/hooks";

export default function LeadPeekDrawer({ lead, open, onOpenChange }) {
  const masterData = useMasterDataMaps();

  if (!lead) return null;

  const stageName = masterData.stageName(lead.current_stage);
  const pipelineName = masterData.pipelineName(lead.pipeline);
  const sourceName = masterData.sourceName(lead.source);
  const val = Number(lead.total_value || 0);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="fixed right-0 top-0 bottom-0 h-dvh w-full max-w-md translate-x-0 translate-y-0 rounded-none border-l border-border bg-surface p-0 shadow-2xl flex flex-col">
        {/* Drawer Header */}
        <div className="flex items-center justify-between border-b border-border bg-[#F8FAF7] dark:bg-[#182823] px-6 py-4.5 shrink-0">
          <div className="flex items-center gap-2">
            <span className="w-7 h-7 rounded-lg bg-primary-soft text-primary flex items-center justify-center font-bold text-xs">
              {(lead.name || "?").slice(0, 2).toUpperCase()}
            </span>
            <div>
              <DialogTitle className="text-base font-bold font-sans text-[#113D37] dark:text-[#E8F0E9]">Quick Lead Peek</DialogTitle>
              <span className="text-xs text-muted-foreground">ID: #{lead.id}</span>
            </div>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full" onClick={() => onOpenChange(false)}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Identity & Status */}
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={lead.status} />
              {val >= 100000 && (
                <Badge className="bg-[#FFE7DC] dark:bg-amber-950/60 text-[#E0532A] dark:text-[#FFA07A] border border-[#F6BCA0] dark:border-amber-800/50 text-[10px] font-bold">
                  🔥 High Value Deal
                </Badge>
              )}
            </div>
            <h2 className="font-display text-2xl font-bold text-[#113D37] dark:text-[#E8F0E9] tracking-tight">{lead.name}</h2>
            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
              <Building2 className="h-3.5 w-3.5 text-primary shrink-0" />
              <span className="font-semibold text-foreground">{lead.company_name || "Independent Account"}</span>
            </p>
          </div>

          {/* Key Metrics Strip */}
          <div className="grid grid-cols-2 gap-3 rounded-xl border border-border bg-[var(--surface-sunken)] p-3.5">
            <div>
              <span className="text-[11px] font-medium text-muted-foreground block">Total Deal Value</span>
              <span className="font-mono text-lg font-bold text-[#113D37] dark:text-[#E8F0E9]">
                {lead.total_value ? `₹${val.toLocaleString("en-IN")}` : "₹0"}
              </span>
            </div>
            <div>
              <span className="text-[11px] font-medium text-muted-foreground block">Current Stage</span>
              <span className="text-xs font-bold text-primary truncate block mt-1">
                {stageName || "In Progress"}
              </span>
            </div>
          </div>

          {/* Contact Details */}
          <div className="space-y-3 rounded-xl border border-border bg-surface p-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Contact Information</h3>
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-2">
                  <Mail className="h-3.5 w-3.5 text-primary" /> Email
                </span>
                <span className="font-medium text-foreground">{lead.email || "—"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-2">
                  <Phone className="h-3.5 w-3.5 text-primary" /> Phone
                </span>
                <span className="font-mono font-medium text-foreground">{lead.phone || "—"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-2">
                  <Layers className="h-3.5 w-3.5 text-primary" /> Pipeline
                </span>
                <span className="font-medium text-foreground">{pipelineName || "Sales Funnel"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-2">
                  <Calendar className="h-3.5 w-3.5 text-primary" /> Source
                </span>
                <span className="font-medium text-foreground">{sourceName || "Direct"}</span>
              </div>
            </div>
          </div>

          {/* Quick Notes / Actions */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Quick Actions</h3>
            <div className="grid grid-cols-2 gap-2">
              <Button variant="outline" size="sm" asChild className="text-xs font-semibold">
                <Link to={`/quotations/new?lead=${lead.id}`}>+ New quote</Link>
              </Button>
              <Button variant="outline" size="sm" asChild className="text-xs font-semibold">
                <Link to={`/tasks/new?lead=${lead.id}`}>+ New task</Link>
              </Button>
            </div>
          </div>
        </div>

        {/* Drawer Footer */}
        <div className="border-t border-border bg-[#F8FAF7] dark:bg-[#182823] p-4 shrink-0">
          <Button asChild className="w-full bg-[#113D37] dark:bg-[#1C6357] text-white hover:bg-[#0A2B26] font-semibold rounded-[9px] shadow-xs">
            <Link to={`/leads/${lead.id}`}>
              Open Full 360 Workspace <ExternalLink className="h-3.5 w-3.5 ml-2" />
            </Link>
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
