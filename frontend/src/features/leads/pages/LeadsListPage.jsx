// Leads list: server-side search/status/ordering/pagination via URL params
// (shareable links, back-button friendly). Filters mirror the LeadListCreateView
// query params in API_CONTRACT.md.

import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { LayoutGrid, Table2, Search, Users, DollarSign, CheckCircle, XCircle, ArrowRight, Eye, Download, SlidersHorizontal, CheckSquare, Square } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { useMasterDataMaps } from "@/features/crm/hooks";
import { getPipelineStages } from "@/features/crm/api";
import { crmKeys } from "@/api/queryKeys";
import { useLeads } from "../hooks";
import KanbanBoard from "../components/KanbanBoard";
import LeadPeekDrawer from "../components/LeadPeekDrawer";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import StatusBadge from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";

const STATUS_FILTERS = [
  { id: "ALL", label: "All leads", dotColor: "bg-muted-foreground" },
  { id: "ACTIVE", label: "Active", dotColor: "bg-success" },
  { id: "CONVERTED", label: "Converted", dotColor: "bg-primary" },
  { id: "LOST", label: "Lost", dotColor: "bg-destructive" },
];

export default function LeadsListPage() {
  const { resolved } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [peekLead, setPeekLead] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [density, setDensity] = useState("comfortable");

  const page = Number(searchParams.get("page") ?? "1");
  const search = searchParams.get("search") ?? "";
  const status = searchParams.get("status") ?? "";
  const ordering = searchParams.get("ordering") ?? "";
  const viewParam = searchParams.get("view");
  const view = viewParam === "board" ? "board" : "list";

  const setViewSynced = (next) => {
    setSearchParams(
      (previous) => {
        const nextParams = new URLSearchParams(previous);
        if (next && next !== "list") nextParams.set("view", next);
        else nextParams.delete("view");
        return nextParams;
      },
      { replace: true },
    );
  };

  const updateParam = (key, value) => {
    setSearchParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (value) {
          next.set(key, value);
        } else {
          next.delete(key);
        }
        if (key !== "page") {
          next.delete("page");
        }
        return next;
      },
      { replace: true },
    );
  };

  const leadsQuery = useLeads({
    page,
    search: search || undefined,
    status: status || undefined,
    ordering: ordering || undefined,
    page_size: 10,
  });

  const allLeadsQuery = useLeads({ page: 1, page_size: 100 });
  const allLeadsList = Array.isArray(allLeadsQuery.data)
    ? allLeadsQuery.data
    : Array.isArray(allLeadsQuery.data?.results)
      ? allLeadsQuery.data.results
      : [];

  const rawData = leadsQuery.data;
  const rawRows = Array.isArray(rawData)
    ? rawData
    : Array.isArray(rawData?.results)
      ? rawData.results
      : [];

  const filteredRows = rawRows.filter((lead) => {
    if (status && status !== "ALL" && lead.status !== status) return false;
    if (search) {
      const query = search.toLowerCase();
      const nameMatch = lead.name?.toLowerCase().includes(query);
      const emailMatch = lead.email?.toLowerCase().includes(query);
      const phoneMatch = lead.phone?.toLowerCase().includes(query);
      const companyMatch = lead.company_name?.toLowerCase().includes(query);
      return nameMatch || emailMatch || phoneMatch || companyMatch;
    }
    return true;
  });

  const rows = filteredRows;
  const count = rawData?.count ?? filteredRows.length;
  const canCreate = hasPermission(resolved, "add_lead");
  const masterData = useMasterDataMaps();

  const stagesQuery = useQuery({
    queryKey: [...crmKeys.pipelineStages(null), "all"],
    queryFn: async () => {
      const data = await getPipelineStages(null);
      return Array.isArray(data) ? data : (data?.results ?? []);
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  const stagesData = stagesQuery.data ?? [];

  // Summary Metrics
  const activeCount = allLeadsList.filter((l) => l.status === "ACTIVE").length;
  const convertedCount = allLeadsList.filter((l) => l.status === "CONVERTED").length;
  const lostCount = allLeadsList.filter((l) => l.status === "LOST").length;
  const totalPipelineVal = allLeadsList.reduce((acc, l) => acc + Number(l.total_value || 0), 0);
  const formattedPipelineVal = totalPipelineVal >= 100000
    ? `₹${(totalPipelineVal / 100000).toFixed(1)}L`
    : `₹${totalPipelineVal.toLocaleString("en-IN")}`;

  // Selection Handlers
  const toggleSelectAll = () => {
    if (selectedIds.size === rows.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(rows.map((r) => r.id)));
    }
  };

  const toggleSelectRow = (id) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  // CSV Export
  const exportToCsv = () => {
    const toExport = selectedIds.size > 0
      ? rows.filter((r) => selectedIds.has(r.id))
      : rows;

    const headers = ["ID", "Name", "Company", "Email", "Phone", "Status", "Stage", "Value", "Source"];
    const csvRows = [
      headers.join(","),
      ...toExport.map((l) => [
        l.id,
        `"${l.name || ""}"`,
        `"${l.company_name || ""}"`,
        `"${l.email || ""}"`,
        `"${l.phone || ""}"`,
        l.status,
        `"${masterData.stageName(l.current_stage) || ""}"`,
        l.total_value || 0,
        `"${masterData.sourceName(l.source) || ""}"`,
      ].join(",")),
    ];

    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `DemoCRM_Leads_Export_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6 p-6 lg:p-8 relative">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-[28px] font-extrabold tracking-tight text-[#113D37] dark:text-[#E8F0E9]">Leads Management</h1>
          <p className="text-[13px] text-muted-foreground mt-0.5">Track, progress, and convert deals across your sales pipeline.</p>
        </div>
        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={exportToCsv}
            className="text-xs font-semibold rounded-[9px] border-border bg-surface hover:bg-muted"
          >
            <Download className="h-3.5 w-3.5 mr-1.5 text-primary" /> Export CSV
          </Button>
          {canCreate ? (
            <Button asChild className="bg-[#FF6A3D] text-[#2B1206] hover:bg-[#E0532A] hover:text-white rounded-[9px] font-semibold shadow-xs">
              <Link to="/leads/new">+ New lead</Link>
            </Button>
          ) : null}
        </div>
      </div>

      {/* Summary KPI Strip — Balanced Visual Identity */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 rounded-[20px] bg-surface border border-border shadow-sm overflow-hidden divide-y sm:divide-y-0 sm:divide-x divide-border">
        <div className="p-5.5 hover:bg-primary-soft/10 transition-colors">
          <span className="text-[12px] font-semibold text-muted-foreground flex items-center gap-2">
            <span className="w-6 h-6 rounded-md bg-primary-soft text-primary flex items-center justify-center">
              <Users className="h-3.5 w-3.5" />
            </span>
            Active Deals
          </span>
          <div className="mt-3 font-mono text-[26px] font-bold text-foreground">
            {allLeadsQuery.isLoading ? "—" : activeCount}
          </div>
          <span className="text-[11px] text-muted-foreground font-medium">In active pipeline</span>
        </div>

        <div className="p-5.5 bg-gradient-to-br from-[#113D37] to-[#0A2B26] text-white">
          <span className="text-[12px] font-semibold text-[#B2D8CD] flex items-center gap-2">
            <span className="w-6 h-6 rounded-md bg-white/15 text-[#FF9770] flex items-center justify-center">
              <DollarSign className="h-3.5 w-3.5" />
            </span>
            Total Deal Value
          </span>
          <div className="mt-3 font-mono text-[26px] font-bold text-white">
            {allLeadsQuery.isLoading ? "—" : formattedPipelineVal}
          </div>
          <span className="text-[11px] text-[#9FC1B6] font-medium">Active pipeline volume</span>
        </div>

        <div className="p-5.5 hover:bg-success-soft/20 transition-colors">
          <span className="text-[12px] font-semibold text-muted-foreground flex items-center gap-2">
            <span className="w-6 h-6 rounded-md bg-success-soft text-success flex items-center justify-center">
              <CheckCircle className="h-3.5 w-3.5" />
            </span>
            Converted
          </span>
          <div className="mt-3 font-mono text-[26px] font-bold text-success">
            {allLeadsQuery.isLoading ? "—" : convertedCount}
          </div>
          <span className="text-[11px] text-muted-foreground font-medium">Won customer accounts</span>
        </div>

        <div className="p-5.5 hover:bg-destructive/5 transition-colors">
          <span className="text-[12px] font-semibold text-muted-foreground flex items-center gap-2">
            <span className="w-6 h-6 rounded-md bg-destructive/10 text-destructive flex items-center justify-center">
              <XCircle className="h-3.5 w-3.5" />
            </span>
            Lost Deals
          </span>
          <div className="mt-3 font-mono text-[26px] font-bold text-destructive">
            {allLeadsQuery.isLoading ? "—" : lostCount}
          </div>
          <span className="text-[11px] text-muted-foreground font-medium">Closed / unreached</span>
        </div>
      </div>

      {/* Toolbar: Search, Status Chips & View/Density Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search Box */}
          <div className="relative flex items-center bg-surface border border-border rounded-[10px] px-3 py-1.5 w-64 md:w-72 shadow-sm">
            <Search className="h-4 w-4 text-muted-foreground mr-2 shrink-0" />
            <input
              type="text"
              placeholder="Search name, company, email…"
              className="bg-transparent border-none outline-none text-xs text-foreground placeholder:text-muted-foreground w-full"
              defaultValue={search}
              onChange={(event) => updateParam("search", event.target.value.trim())}
            />
          </div>

          {/* Filter Chips */}
          <div className="flex flex-wrap items-center gap-1.5">
            {STATUS_FILTERS.map((chip) => {
              const isActive = (!status && chip.id === "ALL") || status === chip.id;
              return (
                <button
                  key={chip.id}
                  type="button"
                  onClick={() => updateParam("status", chip.id === "ALL" ? "" : chip.id)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
                    isActive
                      ? "bg-primary-soft border-primary/30 text-primary shadow-xs"
                      : "bg-surface border-border text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${chip.dotColor}`} />
                  {chip.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Density Toggle */}
          <div className="hidden sm:inline-flex items-center rounded-[10px] bg-[var(--surface-sunken)] p-1 border border-border">
            <button
              type="button"
              onClick={() => setDensity(density === "compact" ? "comfortable" : "compact")}
              className="inline-flex items-center gap-1.5 rounded-[7px] px-2.5 py-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-all cursor-pointer"
              title="Toggle Row Density"
            >
              <SlidersHorizontal className="h-3 w-3 text-primary" />
              <span className="capitalize">{density}</span>
            </button>
          </div>

          {/* View Switcher: List vs Board */}
          <div className="inline-flex items-center rounded-[10px] bg-[var(--surface-sunken)] p-1 border border-border">
            <button
              type="button"
              onClick={() => setViewSynced("list")}
              className={`inline-flex items-center gap-1.5 rounded-[7px] px-3 py-1 text-xs font-semibold transition-all cursor-pointer ${
                view === "list"
                  ? "bg-surface text-primary shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Table2 className="h-3.5 w-3.5" />
              List
            </button>
            <button
              type="button"
              onClick={() => setViewSynced("board")}
              className={`inline-flex items-center gap-1.5 rounded-[7px] px-3 py-1 text-xs font-semibold transition-all cursor-pointer ${
                view === "board"
                  ? "bg-surface text-primary shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <LayoutGrid className="h-3.5 w-3.5" />
              Board
            </button>
          </div>
        </div>
      </div>

      {/* Main Content: Table or Board */}
      {leadsQuery.isError ? (
        <PageError error={leadsQuery.error} onRetry={leadsQuery.refetch} />
      ) : view === "board" ? (
        <KanbanBoard
          stages={stagesData}
          leads={rows}
          isLoading={leadsQuery.isLoading || stagesQuery.isLoading}
          onLeadClick={(lead) => navigate(`/leads/${lead.id}`)}
        />
      ) : (
        <div className={`rounded-[16px] bg-surface border border-border shadow-sm overflow-hidden ${density === "compact" ? "[&_td]:py-1.5 [&_th]:py-2 text-xs" : ""}`}>
          <DataTable
            columns={[
              {
                key: "select",
                header: () => (
                  <button
                    onClick={toggleSelectAll}
                    className="p-1 hover:text-primary transition-colors cursor-pointer"
                    title={selectedIds.size === rows.length ? "Deselect all" : "Select all"}
                  >
                    {rows.length > 0 && selectedIds.size === rows.length ? (
                      <CheckSquare className="h-4 w-4 text-primary" />
                    ) : (
                      <Square className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>
                ),
                render: (lead) => (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleSelectRow(lead.id);
                    }}
                    className="p-1 hover:text-primary transition-colors cursor-pointer"
                  >
                    {selectedIds.has(lead.id) ? (
                      <CheckSquare className="h-4 w-4 text-primary" />
                    ) : (
                      <Square className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>
                ),
              },
              {
                key: "name",
                header: "Lead & Company",
                sortable: true,
                render: (lead) => {
                  const val = Number(lead.total_value || 0);
                  const isHigh = val >= 100000;
                  return (
                    <div className="flex items-center gap-3 py-0.5">
                      <div className="w-8 h-8 rounded-full bg-primary-soft text-primary flex items-center justify-center font-display font-bold text-xs shrink-0 border border-primary/20">
                        {(lead.name || "?").slice(0, 2).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <Link
                            to={`/leads/${lead.id}`}
                            className="font-display font-semibold text-[13.5px] text-foreground hover:text-primary transition-colors block truncate"
                          >
                            {lead.name}
                          </Link>
                          {isHigh && (
                            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded text-[10px] font-bold bg-[#FFE7DC] text-[#E0532A] border border-[#F6BCA0]">
                              🔥 Hot
                            </span>
                          )}
                        </div>
                        <span className="text-[11px] text-muted-foreground block truncate">
                          {lead.company_name || "Independent Account"}
                        </span>
                      </div>
                    </div>
                  );
                },
              },
              {
                key: "contact",
                header: "Contact",
                render: (lead) => (
                  <div className="text-xs space-y-0.5">
                    <div className="text-foreground truncate max-w-44">{lead.email || "—"}</div>
                    <div className="font-mono text-muted-foreground">{lead.phone || "—"}</div>
                  </div>
                ),
              },
              {
                key: "current_stage",
                header: "Stage",
                render: (lead) => {
                  const stageName = masterData.stageName(lead.current_stage);
                  return stageName ? (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-primary-soft text-primary dark:text-[#A8E0D2] border border-primary/30">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary dark:bg-[#4CAF9A]" />
                      {stageName}
                    </span>
                  ) : (
                    "—"
                  );
                },
              },
              {
                key: "status",
                header: "Status",
                sortable: true,
                render: (lead) => <StatusBadge status={lead.status} />,
              },
              {
                key: "total_value",
                header: "Deal Value",
                sortable: true,
                render: (lead) => (
                  <span className="font-mono font-bold text-[13px] text-foreground">
                    {lead.total_value != null ? `₹${Number(lead.total_value).toLocaleString("en-IN")}` : "—"}
                  </span>
                ),
              },
              {
                key: "source",
                header: "Source",
                render: (lead) => (
                  <span className="text-xs text-muted-foreground">
                    {masterData.sourceName(lead.source) ?? "—"}
                  </span>
                ),
              },
              {
                key: "actions",
                header: "",
                render: (lead) => (
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setPeekLead(lead)}
                      title="Quick Peek Drawer"
                      className="h-7 w-7 text-muted-foreground hover:text-primary hover:bg-primary-soft cursor-pointer"
                    >
                      <Eye className="h-3.5 w-3.5" />
                    </Button>
                    <Button variant="ghost" size="sm" asChild className="h-7 px-2 text-xs font-semibold text-primary dark:text-[#52C4AC] hover:text-primary">
                      <Link to={`/leads/${lead.id}`}>
                        Workspace <ArrowRight className="h-3 w-3 ml-1" />
                      </Link>
                    </Button>
                  </div>
                ),
              },
            ]}
            rows={rows}
            getRowId={(row) => row.id}
            isLoading={leadsQuery.isLoading}
            emptyState={
              <EmptyState
                title="No leads found"
                description={
                  search || status
                    ? "Try adjusting the search or filter criteria."
                    : canCreate
                      ? "Create your first lead to start closing deals."
                      : undefined
                }
                ctaLabel={canCreate && !search && !status ? "New lead" : undefined}
                ctaTo={canCreate ? "/leads/new" : undefined}
              />
            }
            sortValue={ordering}
            onSortChange={(value) => updateParam("ordering", value)}
            page={page}
            pageSize={10}
            count={count}
            onPageChange={(nextPage) => updateParam("page", String(nextPage))}
          />
        </div>
      )}

      {/* Floating Bulk Action Bar */}
      {selectedIds.size > 0 && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 bg-[#113D37] text-white px-5 py-3 rounded-2xl shadow-2xl border border-white/20 animate-in fade-in slide-in-from-bottom-4 duration-200">
          <div className="text-xs font-medium flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-[#FF6A3D] text-[#2B1206] font-mono font-bold text-[11px] flex items-center justify-center">
              {selectedIds.size}
            </span>
            <span>deals selected</span>
          </div>

          <div className="h-4 w-px bg-white/20" />

          <Button
            size="sm"
            onClick={exportToCsv}
            className="h-7 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold rounded-lg"
          >
            <Download className="h-3 w-3 mr-1 text-[#FF9770]" /> Export ({selectedIds.size})
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => setSelectedIds(new Set())}
            className="h-7 text-xs text-[#9FC1B6] hover:text-white hover:bg-white/10"
          >
            Clear selection
          </Button>
        </div>
      )}

      {/* Slide-Over Quick Peek Drawer */}
      <LeadPeekDrawer
        lead={peekLead}
        open={Boolean(peekLead)}
        onOpenChange={(open) => !open && setPeekLead(null)}
      />
    </div>
  );
}
