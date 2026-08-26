// Quotations list with optional ?lead= filter (deep-linked from lead pages).

import { Link, useSearchParams } from "react-router-dom";
import { useQuotations } from "../hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import StatusBadge from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { toMoney } from "@/utils/formatters";

export default function QuotationsListPage() {
  const [searchParams] = useSearchParams();
  const leadFilter = searchParams.get("lead") ?? "";

  const quotationsQuery = useQuotations({ lead: leadFilter || undefined });
  const rows = quotationsQuery.data?.results ?? quotationsQuery.data ?? [];

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Quotations</h1>
        <Button asChild>
          <Link to={leadFilter ? `/quotations/new?lead=${leadFilter}` : "/quotations/new"}>
            New quotation
          </Link>
        </Button>
      </div>

      {quotationsQuery.isError ? (
        <PageError error={quotationsQuery.error} onRetry={quotationsQuery.refetch} />
      ) : (
        <DataTable
          columns={[
            {
              key: "quotation_number",
              header: "Number",
              render: (quotation) => (
                <Link
                  to={`/quotations/${quotation.id}`}
                  className="font-medium hover:underline"
                >
                  {quotation.quotation_number}
                </Link>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (quotation) => <StatusBadge status={quotation.status} />,
            },
            {
              key: "total",
              header: "Total",
              render: (quotation) =>
                toMoney(quotation.current_version_detail?.total_amount),
            },
            {
              key: "created_at",
              header: "Created",
              render: (quotation) =>
                quotation.created_at
                  ? new Date(quotation.created_at).toLocaleDateString()
                  : "—",
            },
          ]}
          rows={rows}
          getRowId={(row) => row.id}
          isLoading={quotationsQuery.isLoading}
          emptyState={
            <EmptyState
              title="No quotations found"
              description="Create a draft quotation from an ACTIVE lead."
            />
          }
          page={1}
          pageSize={Math.max(rows.length, 1)}
          count={rows.length}
        />
      )}
    </div>
  );
}
