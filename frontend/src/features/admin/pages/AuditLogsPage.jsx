import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function AuditLogsPage() {
  const q = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => apiClient.get(endpoints.crm.auditLogs).then((r) => r.data),
  });
  if (q.isLoading) return <PageLoader label="Loading audit logs…" />;
  if (q.isError) return <PageError error={q.error} onRetry={q.refetch} />;
  const rows = q.data?.results ?? q.data ?? [];
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Audit Logs</h1>
      <Card className="rounded-xl">
        <CardHeader><CardTitle className="text-sm">Recent changes</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-2">
          {!rows.length ? <p className="text-sm text-muted-foreground">No audit logs.</p> : rows.slice(0, 50).map((log) => (
            <div key={log.id} className="flex items-center justify-between rounded border px-3 py-1.5 text-sm">
              <span><Badge variant="outline">{log.entity_type}</Badge> {log.action} — {log.entity_id?.slice(0,8)}</span>
              <span className="text-xs text-muted-foreground">{log.created_at ? new Date(log.created_at).toLocaleString() : ""}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
