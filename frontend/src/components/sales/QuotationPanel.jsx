import { Link } from "react-router-dom";
import { FileText } from "lucide-react";
import { useQuotations } from "@/features/quotations/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function QuotationPanel({ leadId, requiresQuotation }) {
  const q = useQuotations({ lead: leadId });
  const rows = q.data?.results ?? q.data ?? [];
  const latest = Array.isArray(rows) ? rows[0] : null;

  if (!requiresQuotation && !latest) return null;

  return (
    <Card className="rounded-[16px] border-outline bg-surface shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold">Stage quotation</CardTitle>
          {requiresQuotation ? <Badge className="bg-primary-soft text-primary border-transparent text-[11px] font-medium normal-case tracking-normal">Required for won</Badge> : latest ? <Badge variant={latest.status === "ACCEPTED" ? "default" : "secondary"}>{latest.status}</Badge> : <Badge variant="outline">No quotation</Badge>}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {!latest ? (
          <div className="rounded-[16px] border border-dashed border-outline bg-surface p-4 text-center">
            <div className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Estimated total value</div>
            <div className="my-1.5 font-mono text-2xl font-semibold text-on-surface">—</div>
            <p className="mb-3 text-[11.5px] leading-relaxed text-muted-foreground">Quotation approval is required before transitioning to Closed Won / Customer conversion.</p>
            <Button asChild variant="default" className="w-full"><Link to={`/quotations/new?lead=${leadId}`} className="inline-flex items-center gap-1.5"><FileText className="h-4 w-4" />Generate formal quotation</Link></Button>
          </div>
        ) : (
          <div className="rounded-[16px] border border-dashed border-outline bg-surface p-4 text-center">
            <div className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Estimated total value</div>
            <div className="my-1.5 font-mono text-2xl font-semibold text-on-surface">₹{latest.current_version_detail?.total_amount ?? latest.current_version?.total_amount ?? latest.total_amount ?? "—"}</div>
            <div className="mb-3 text-xs text-muted-foreground font-mono">{latest.quotation_number ?? latest.id?.slice(0,8)} · <Badge variant="outline" className="ml-1 text-[11px]">{latest.status}</Badge></div>
            <div className="flex gap-2 justify-center">
              <Button asChild variant="outline" size="sm"><Link to={`/quotations/${latest.id}`}>Open</Link></Button>
              {latest.status === "DRAFT" ? <Button asChild variant="default" size="sm"><Link to={`/quotations/${latest.id}`}>Submit</Link></Button> : null}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
