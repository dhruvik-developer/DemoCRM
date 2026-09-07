// Quotations list with optional ?lead= filter (deep-linked from lead pages).

import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FileText, Plus, DollarSign, CheckCircle2, Send, ArrowRight, Trash2 } from "lucide-react";
import { useQuotations, useDeleteQuotation } from "../hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import StatusBadge from "@/components/common/StatusBadge";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { toMoney } from "@/utils/formatters";

export default function QuotationsListPage() {
  const [searchParams] = useSearchParams();
  const leadFilter = searchParams.get("lead") ?? "";
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [statusFilter, setStatusFilter] = useState("ALL");

  const quotationsQuery = useQuotations({ lead: leadFilter || undefined });
  const deleteQuotation = useDeleteQuotation();
  const rawRows = (quotationsQuery.data?.results ?? quotationsQuery.data ?? []).filter(Boolean);

  const filteredRows = rawRows.filter((q) => {
    if (statusFilter !== "ALL" && q.status !== statusFilter) return false;
    return true;
  });

  const totalValue = rawRows.reduce((acc, q) => acc + Number(q?.current_version_detail?.total_amount || q?.grand_total || 0), 0);
  const draftCount = rawRows.filter((q) => q.status === "DRAFT").length;
  const sentCount = rawRows.filter((q) => ["SENT", "APPROVED"].includes(q.status)).length;
  const acceptedCount = rawRows.filter((q) => q.status === "ACCEPTED").length;

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6 p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-[28px] font-extrabold tracking-tight text-[#113D37] dark:text-[#E8F0E9]">Quotations & Pricing</h1>
          <p className="text-[13px] text-muted-foreground mt-0.5">Generate, approve, and track client proposals and commercial agreements.</p>
        </div>
        <Button asChild className="bg-[#FF6A3D] text-[#2B1206] hover:bg-[#E0532A] hover:text-white rounded-[9px] font-semibold shadow-xs">
          <Link to={leadFilter ? `/quotations/new?lead=${leadFilter}` : "/quotations/new"}>
            <Plus className="h-4 w-4 mr-1" /> New quotation
          </Link>
        </Button>
      </div>

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 rounded-[20px] bg-surface border border-border shadow-sm overflow-hidden divide-y sm:divide-y-0 sm:divide-x divide-border">
        <div className="p-5.5 hover:bg-primary-soft/10 transition-colors">
          <span className="text-[12px] font-semibold text-muted-foreground flex items-center gap-2">
            <span className="w-6 h-6 rounded-md bg-primary-soft text-primary flex items-center justify-center">
              <FileText className="h-3.5 w-3.5" />
            </span>
            Total Quotes
          </span>
          <div className="mt-3 font-mono text-[26px] font-bold text-foreground">
            {quotationsQuery.isLoading ? "—" : rawRows.length}
          </div>
          <span className="text-[11px] text-muted-foreground font-medium">Generated proposals</span>
        </div>

        <div className="p-5.5 bg-gradient-to-br from-[#113D37] to-[#0A2B26] text-white">
          <span className="text-[12px] font-semibold text-[#B2D8CD] flex items-center gap-2">
            <span className="w-6 h-6 rounded-md bg-white/15 text-[#FF9770] flex items-center justify-center">
              <DollarSign className="h-3.5 w-3.5" />
            </span>
            Quoted Value
          </span>
          <div className="mt-3 font-mono text-[26px] font-bold text-white">
            ₹{totalValue >= 100000 ? `${(totalValue / 100000).toFixed(1)}L` : totalValue.toLocaleString("en-IN")}
          </div>
          <span className="text-[11px] text-[#9FC1B6] font-medium">Across all proposals</span>
        </div>

        <div className="p-5.5 hover:bg-info/10 transition-colors">
          <span className="text-[12px] font-semibold text-muted-foreground flex items-center gap-2">
            <span className="w-6 h-6 rounded-md bg-info/10 text-info flex items-center justify-center">
              <Send className="h-3.5 w-3.5" />
            </span>
            Out for Review
          </span>
          <div className="mt-3 font-mono text-[26px] font-bold text-info">
            {quotationsQuery.isLoading ? "—" : sentCount}
          </div>
          <span className="text-[11px] text-muted-foreground font-medium">Sent to clients</span>
        </div>

        <div className="p-5.5 hover:bg-success-soft/20 transition-colors">
          <span className="text-[12px] font-semibold text-muted-foreground flex items-center gap-2">
            <span className="w-6 h-6 rounded-md bg-success-soft text-success flex items-center justify-center">
              <CheckCircle2 className="h-3.5 w-3.5" />
            </span>
            Accepted Deals
          </span>
          <div className="mt-3 font-mono text-[26px] font-bold text-success">
            {quotationsQuery.isLoading ? "—" : acceptedCount}
          </div>
          <span className="text-[11px] text-muted-foreground font-medium">Won contracts</span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-1.5">
        {[
          { id: "ALL", label: "All quotes" },
          { id: "DRAFT", label: `Drafts (${draftCount})` },
          { id: "SENT", label: `Sent (${sentCount})` },
          { id: "ACCEPTED", label: `Accepted (${acceptedCount})` },
        ].map((tab) => {
          const isActive = statusFilter === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setStatusFilter(tab.id)}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
                isActive
                  ? "bg-primary-soft border-primary/30 text-primary shadow-xs"
                  : "bg-surface border-border text-muted-foreground hover:text-foreground hover:bg-muted/50"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Table Card */}
      {quotationsQuery.isError ? (
        <PageError error={quotationsQuery.error} onRetry={quotationsQuery.refetch} />
      ) : (
        <div className="rounded-[16px] bg-surface border border-border shadow-sm overflow-hidden">
          <DataTable
            columns={[
              {
                key: "quotation_number",
                header: "Quotation #",
                render: (quotation) => (
                  <div className="flex items-center gap-2.5 py-1">
                    <div className="w-7 h-7 rounded-lg bg-primary-soft text-primary flex items-center justify-center text-xs font-bold shrink-0">
                      <FileText className="h-3.5 w-3.5" />
                    </div>
                    <Link
                      to={`/quotations/${quotation?.id}`}
                      className="font-mono font-bold text-[13px] text-foreground hover:text-primary transition-colors"
                    >
                      {quotation?.quotation_number}
                    </Link>
                  </div>
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (quotation) => <StatusBadge status={quotation?.status} />,
              },
              {
                key: "total",
                header: "Total Amount",
                render: (quotation) => (
                  <span className="font-mono font-bold text-[13px] text-foreground">
                    ₹{toMoney(quotation?.current_version_detail?.total_amount || quotation?.grand_total || 0)}
                  </span>
                ),
              },
              {
                key: "created_at",
                header: "Created Date",
                render: (quotation) => (
                  <span className="text-xs text-muted-foreground">
                    {quotation?.created_at ? new Date(quotation.created_at).toLocaleDateString() : "—"}
                  </span>
                ),
              },
              {
                key: "actions",
                header: "",
                render: (quotation) => (
                  <div className="flex items-center justify-end gap-2">
                    {quotation?.status === "DRAFT" ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-destructive hover:bg-destructive/10 text-xs px-2"
                        onClick={() => setDeleteTarget(quotation)}
                      >
                        <Trash2 className="h-3.5 w-3.5 mr-1" /> Delete
                      </Button>
                    ) : null}
                    <Button asChild variant="ghost" size="sm" className="h-7 px-2.5 text-xs font-semibold text-primary">
                      <Link to={`/quotations/${quotation?.id}`}>
                        View <ArrowRight className="h-3 w-3 ml-1" />
                      </Link>
                    </Button>
                  </div>
                ),
              },
            ]}
            rows={filteredRows}
            getRowId={(row) => row?.id ?? Math.random().toString(36)}
            isLoading={quotationsQuery.isLoading}
            emptyState={
              <EmptyState
                title="No quotations found"
                description="Create a draft quotation from an active lead workspace."
              />
            }
            page={1}
            pageSize={Math.max(filteredRows.length, 1)}
            count={filteredRows.length}
          />
        </div>
      )}

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete draft quotation?"
        description={`This will permanently delete ${deleteTarget?.quotation_number ?? ""} (draft). Sent/accepted quotations are preserved for audit and cannot be deleted.`}
        confirmLabel="Delete draft"
        destructive
        loading={deleteQuotation.isPending}
        onConfirm={() => deleteTarget && deleteQuotation.mutateAsync(deleteTarget.id).then(() => setDeleteTarget(null))}
      />
    </div>
  );
}
