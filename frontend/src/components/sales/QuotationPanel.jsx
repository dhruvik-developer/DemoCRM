import { Link } from "react-router-dom";
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
    <Card className="rounded-[14px] border-[#E2E8F0] shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold">Stage Quotation</CardTitle>
          {requiresQuotation ? <Badge className="bg-[#EEF2FF] text-[#4F46E5] border-[#C7D2FE] text-[11px] font-bold">Required for Won</Badge> : latest ? <Badge variant={latest.status === "ACCEPTED" ? "default" : "secondary"}>{latest.status}</Badge> : <Badge variant="outline">No quotation</Badge>}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {!latest ? (
          <div className="rounded-[10px] border border-dashed border-[#E2E8F0] bg-gradient-to-b from-[#FAFBFC] to-[#F1F5F9] p-4 text-center">
            <div className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Estimated Total Value</div>
            <div className="my-1.5 text-[22px] font-extrabold tracking-[-0.02em] text-[#0F172A]">—</div>
            <p className="mb-3 text-[11.5px] leading-relaxed text-muted-foreground">Quotation approval is required before transitioning to Closed Won / Customer conversion.</p>
            <Button asChild className="w-full bg-[#2563EB] hover:bg-[#1D4ED8]"><Link to={`/quotations/new?lead=${leadId}`}>📄 Generate Formal Quotation</Link></Button>
          </div>
        ) : (
          <div className="rounded-[10px] border border-dashed border-[#E2E8F0] bg-gradient-to-b from-[#FAFBFC] to-[#F1F5F9] p-4 text-center">
            <div className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Estimated Total Value</div>
            <div className="my-1.5 text-[22px] font-extrabold tracking-[-0.02em] text-[#0F172A]">₹{latest.current_version_detail?.total_amount ?? latest.current_version?.total_amount ?? latest.total_amount ?? "—"}</div>
            <div className="mb-3 text-xs text-muted-foreground">{latest.quotation_number ?? latest.id?.slice(0,8)} · <Badge variant="outline" className="ml-1 text-[11px]">{latest.status}</Badge></div>
            <div className="flex gap-2 justify-center">
              <Button asChild variant="outline" size="sm"><Link to={`/quotations/${latest.id}`}>Open</Link></Button>
              {latest.status === "DRAFT" ? <Button asChild size="sm" className="bg-[#2563EB] hover:bg-[#1D4ED8]"><Link to={`/quotations/${latest.id}`}>Submit</Link></Button> : null}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
