// Leads list: server-side search/status/ordering/pagination via URL params
// (shareable links, back-button friendly). Filters mirror the LeadListCreateView
// query params in API_CONTRACT.md.

import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { useMasterDataMaps } from "@/features/crm/hooks";
import { useLeads } from "../hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import StatusBadge from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const LEAD_STATUSES = ["ACTIVE", "LOST", "CONVERTED"];

export default function LeadsListPage() {
  const { resolved } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const page = Number(searchParams.get("page") ?? "1");
  const search = searchParams.get("search") ?? "";
  const status = searchParams.get("status") ?? "";
  const ordering = searchParams.get("ordering") ?? "";

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
          next.delete("page"); // reset to first page on filter change
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

  const rows = leadsQuery.data?.results ?? [];
  const count = leadsQuery.data?.count ?? 0;
  const canCreate = hasPermission(resolved, "add_lead");
  const masterData = useMasterDataMaps();

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Leads</h1>
        {canCreate ? (
          <Button asChild>
            <Link to="/leads/new">New lead</Link>
          </Button>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="Search name, email, phone…"
          className="w-64"
          defaultValue={search}
          onChange={(event) => updateParam("search", event.target.value.trim())}
        />
        <Select value={status || "ALL"} onValueChange={(value) => updateParam("status", value === "ALL" ? "" : value)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All statuses</SelectItem>
            {LEAD_STATUSES.map((value) => (
              <SelectItem key={value} value={value}>
                {value.charAt(0) + value.slice(1).toLowerCase()}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {leadsQuery.isError ? (
        <PageError error={leadsQuery.error} onRetry={leadsQuery.refetch} />
      ) : (
        <DataTable
          columns={[
            {
              key: "name",
              header: "Name",
              sortable: true,
              render: (lead) => (
                <Link
                  to={`/leads/${lead.id}`}
                  className="font-medium hover:underline"
                >
                  {lead.name}
                </Link>
              ),
            },
            { key: "email", header: "Email" },
            { key: "phone", header: "Phone" },
            { key: "company_name", header: "Company" },
            {
              key: "status",
              header: "Status",
              sortable: true,
              render: (lead) => <StatusBadge status={lead.status} />,
            },
            {
              key: "current_stage",
              header: "Stage",
              render: (lead) => masterData.stageName(lead.current_stage) ?? "—",
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
                  ? "Try adjusting the search or filters."
                  : canCreate
                    ? "Create your first lead to get started."
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
      )}
    </div>
  );
}
