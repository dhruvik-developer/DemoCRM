// Customers list with search + pagination, plus the Smart Lookup panel
// (multi-field matching: email / phone / GST / company).

import { Link, useSearchParams } from "react-router-dom";
import { useState } from "react";
import { useCustomers, useSmartLookup } from "../hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

function SmartLookupPanel() {
  const [query, setQuery] = useState("");
  const lookup = useSmartLookup({ query: query.trim() || undefined });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Smart lookup</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Input
          placeholder="Search by email, phone, GST or company…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {lookup.isFetching ? (
          <p className="text-sm text-muted-foreground">Searching…</p>
        ) : null}
        {lookup.data && !lookup.data.match_found ? (
          <p className="text-sm text-muted-foreground">No match found.</p>
        ) : null}
        {lookup.data?.match_found ? (
          <div className="flex flex-col gap-2 text-sm">
            <div className="flex items-center gap-2">
              <Badge variant="outline">Match</Badge>
              <span className="font-medium">
                {lookup.data.account?.company_name ?? "Account"}
              </span>
            </div>
            {(lookup.data.recent ?? []).slice(0, 5).map((customer) => (
              <Link
                key={customer.id}
                to={`/customers/${customer.id}`}
                className="hover:underline"
              >
                {customer.name} — {customer.email ?? customer.phone}
              </Link>
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default function CustomersListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get("page") ?? "1");
  const search = searchParams.get("search") ?? "";

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

  const customersQuery = useCustomers({ page, search: search || undefined });
  const rows = customersQuery.data?.results ?? [];
  const count = customersQuery.data?.count ?? 0;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Customers</h1>

      <SmartLookupPanel />

      <Input
        placeholder="Search customers…"
        className="w-64"
        defaultValue={search}
        onChange={(event) => updateParam("search", event.target.value.trim())}
      />

      {customersQuery.isError ? (
        <PageError error={customersQuery.error} onRetry={customersQuery.refetch} />
      ) : (
        <DataTable
          columns={[
            {
              key: "name",
              header: "Name",
              render: (customer) => (
                <Link
                  to={`/customers/${customer.id}`}
                  className="font-medium hover:underline"
                >
                  {customer.name}
                </Link>
              ),
            },
            { key: "email", header: "Email" },
            { key: "phone", header: "Phone" },
            { key: "company_name", header: "Company" },
            {
              key: "created_at",
              header: "Created",
              render: (customer) =>
                customer.created_at
                  ? new Date(customer.created_at).toLocaleDateString()
                  : "—",
            },
          ]}
          rows={rows}
          getRowId={(row) => row.id}
          isLoading={customersQuery.isLoading}
          emptyState={
            <EmptyState
              title="No customers yet"
              description="Customers are created when a lead is converted (or a quotation is accepted)."
            />
          }
          page={page}
          pageSize={10}
          count={count}
          onPageChange={(nextPage) => updateParam("page", String(nextPage))}
        />
      )}
    </div>
  );
}
