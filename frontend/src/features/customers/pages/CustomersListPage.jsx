// Customers list with search + pagination, plus the Smart Lookup panel
// (multi-field matching: email / phone / GST / company).

import { Link, useSearchParams } from "react-router-dom";
import { useState } from "react";
import { Search, ArrowRight, UserCheck, ShieldCheck, Mail, Phone } from "lucide-react";
import { useCustomers, useSmartLookup } from "../hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function SmartLookupPanel() {
  const [query, setQuery] = useState("");
  const lookup = useSmartLookup({ query: query.trim() || undefined });

  return (
    <Card className="rounded-[18px] border-border bg-surface shadow-sm overflow-hidden">
      <CardHeader className="border-b border-border bg-surface px-5 py-3.5">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm font-semibold font-sans flex items-center gap-2">
              <Search className="h-4 w-4 text-primary" /> Smart Account & Customer Lookup
            </CardTitle>
            <CardDescription className="text-xs text-muted-foreground mt-0.5">
              Instant multi-field resolution across email, phone, GST number, or company name.
            </CardDescription>
          </div>
          {lookup.isFetching && <span className="text-xs text-muted-foreground animate-pulse">Matching…</span>}
        </div>
      </CardHeader>
      <CardContent className="p-5 space-y-3">
        <div className="relative flex items-center bg-[var(--surface-sunken)] border border-border rounded-[10px] px-3.5 py-2 shadow-xs">
          <Search className="h-4 w-4 text-muted-foreground mr-2 shrink-0" />
          <input
            placeholder="Enter client email, +91 phone, GSTIN, or registered company…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="bg-transparent border-none outline-none text-xs text-foreground placeholder:text-muted-foreground w-full font-sans"
          />
        </div>

        {lookup.data && !lookup.data.match_found && query.trim() ? (
          <p className="text-xs text-muted-foreground italic">No matching existing customer record found.</p>
        ) : null}

        {lookup.data?.match_found ? (
          <div className="rounded-[12px] border border-[#BBD7CB] dark:border-emerald-800/40 bg-[#E3EEE8] dark:bg-emerald-950/30 p-3.5 space-y-2">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#113D37] dark:text-[#E8F0E9] bg-white dark:bg-[#182823] px-2 py-0.5 rounded-full shadow-xs">
                <ShieldCheck className="h-3 w-3 text-[#2E8B57]" /> Verified Match
              </span>
              <span className="text-xs font-bold text-[#113D37] dark:text-[#E8F0E9]">
                {lookup.data.account?.company_name ?? "Corporate Account"}
              </span>
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              {(lookup.data.recent ?? []).slice(0, 4).map((customer) => (
                <Link
                  key={customer.id}
                  to={`/customers/${customer.id}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white dark:bg-[#182823] text-xs font-medium text-[#113D37] dark:text-[#E8F0E9] hover:bg-[#113D37] hover:text-white dark:hover:bg-[#1C6357] transition-all shadow-xs"
                >
                  <UserCheck className="h-3.5 w-3.5" />
                  {customer.name} ({customer.email || customer.phone})
                  <ArrowRight className="h-3 w-3 ml-1" />
                </Link>
              ))}
            </div>
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
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6 p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-[28px] font-extrabold tracking-tight text-[#113D37] dark:text-[#E8F0E9]">Customers & Accounts</h1>
          <p className="text-[13px] text-muted-foreground mt-0.5">Manage established client relationships, company profiles, and ledger histories.</p>
        </div>
      </div>

      <SmartLookupPanel />

      <div className="flex items-center justify-between gap-4">
        <div className="relative flex items-center bg-surface border border-border rounded-[10px] px-3 py-1.5 w-64 md:w-72 shadow-sm">
          <Search className="h-4 w-4 text-muted-foreground mr-2 shrink-0" />
          <input
            placeholder="Search customers…"
            className="bg-transparent border-none outline-none text-xs text-foreground placeholder:text-muted-foreground w-full"
            defaultValue={search}
            onChange={(event) => updateParam("search", event.target.value.trim())}
          />
        </div>
        <span className="text-xs text-muted-foreground font-mono">Total: <strong>{count}</strong> accounts</span>
      </div>

      {customersQuery.isError ? (
        <PageError error={customersQuery.error} onRetry={customersQuery.refetch} />
      ) : (
        <div className="rounded-[16px] bg-surface border border-border shadow-sm overflow-hidden">
          <DataTable
            columns={[
              {
                key: "name",
                header: "Customer & Organization",
                render: (customer) => (
                  <div className="flex items-center gap-3 py-1">
                    <div className="w-8 h-8 rounded-full bg-primary-soft text-primary font-display font-bold text-xs flex items-center justify-center shrink-0 border border-primary/20">
                      {(customer.name || "?").slice(0, 2).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <Link
                        to={`/customers/${customer.id}`}
                        className="font-display font-semibold text-[13.5px] text-foreground hover:text-primary transition-colors block truncate"
                      >
                        {customer.name}
                      </Link>
                      <span className="text-[11px] text-muted-foreground block truncate">
                        {customer.company_name || "Independent Account"}
                      </span>
                    </div>
                  </div>
                ),
              },
              {
                key: "email",
                header: "Contact Email",
                render: (customer) => (
                  <div className="flex items-center gap-1.5 text-xs text-foreground">
                    <Mail className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    <span className="truncate max-w-44">{customer.email || "—"}</span>
                  </div>
                ),
              },
              {
                key: "phone",
                header: "Phone",
                render: (customer) => (
                  <div className="flex items-center gap-1.5 font-mono text-xs text-foreground">
                    <Phone className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    <span>{customer.phone || "—"}</span>
                  </div>
                ),
              },
              {
                key: "company_name",
                header: "Company Account",
                render: (customer) => (
                  <span className="text-xs text-foreground font-medium">
                    {customer.company_name || "—"}
                  </span>
                ),
              },
              {
                key: "created_at",
                header: "Customer Since",
                render: (customer) => (
                  <span className="text-xs text-muted-foreground font-mono">
                    {customer.created_at ? new Date(customer.created_at).toLocaleDateString() : "—"}
                  </span>
                ),
              },
              {
                key: "actions",
                header: "",
                render: (customer) => (
                  <div className="flex justify-end">
                    <Button asChild variant="ghost" size="sm" className="h-7 px-2.5 text-xs font-semibold text-primary">
                      <Link to={`/customers/${customer.id}`}>
                        Customer 360 <ArrowRight className="h-3 w-3 ml-1" />
                      </Link>
                    </Button>
                  </div>
                ),
              },
            ]}
            rows={rows}
            getRowId={(row) => row.id}
            isLoading={customersQuery.isLoading}
            emptyState={
              <EmptyState
                title="No customers yet"
                description="Customers are automatically registered when a lead is converted or quotation accepted."
              />
            }
            page={page}
            pageSize={10}
            count={count}
            onPageChange={(nextPage) => updateParam("page", String(nextPage))}
          />
        </div>
      )}
    </div>
  );
}
