import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function AuditLogsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, parseInt(searchParams.get("page") || "1", 10) || 1);
  const pageSize = 20;

  const q = useQuery({
    queryKey: ["audit-logs", page],
    queryFn: () =>
      apiClient
        .get(endpoints.crm.auditLogs, { params: { page, page_size: pageSize } })
        .then((r) => r.data),
    placeholderData: (prev) => prev,
  });
  if (q.isLoading) return <PageLoader label="Loading audit logs…" />;
  if (q.isError) return <PageError error={q.error} onRetry={q.refetch} />;
  const raw = q.data;
  const isPaginated = Array.isArray(raw?.results);
  const allRows = isPaginated ? raw.results : (raw ?? []);
  const totalCount = raw?.count ?? allRows.length;
  const totalPages = raw?.num_pages ?? Math.max(1, Math.ceil(totalCount / pageSize));
  const rows = isPaginated ? allRows : allRows.slice((page - 1) * pageSize, page * pageSize);
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Audit Logs {totalCount ? `(${totalCount})` : ""}</h1>
      <Card className="rounded-xl">
        <CardHeader><CardTitle className="text-sm">Recent changes</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-2">
          {!rows.length ? <p className="text-sm text-muted-foreground">No audit logs.</p> : rows.map((log) => (
            <div key={log.id} className="flex items-center justify-between rounded border px-3 py-1.5 text-sm">
              <span><Badge variant="outline">{log.entity_type}</Badge> {log.action} — {log.entity_id?.slice(0,8)}</span>
              <span className="text-xs text-muted-foreground">{log.created_at ? new Date(log.created_at).toLocaleString() : ""}</span>
            </div>
          ))}
          {totalPages > 1 ? (
            <div className="flex items-center justify-between border-t pt-4">
              <span className="text-xs text-muted-foreground">Page {page} of {totalPages} • {totalCount} total</span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setSearchParams({ page: String(page - 1) })}>Prev</Button>
                <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setSearchParams({ page: String(page + 1) })}>Next</Button>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
