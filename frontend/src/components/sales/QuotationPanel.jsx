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
    <Card className="rounded-xl">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Quotation {requiresQuotation ? "required" : ""}</CardTitle>
          {latest ? <Badge variant={latest.status === "ACCEPTED" ? "default" : "secondary"}>{latest.status}</Badge> : <Badge variant="outline">No quotation</Badge>}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {!latest ? (
          <>
            <p className="text-sm text-muted-foreground">No quotation exists for this stage.</p>
            <Button asChild className="w-fit bg-[#2563EB] hover:bg-[#1D4ED8]"><Link to={`/quotations/new?lead=${leadId}`}>Create quotation</Link></Button>
          </>
        ) : (
          <>
            <div className="text-sm">
              <span className="font-semibold">{latest.quotation_number ?? latest.id?.slice(0,8)}</span>
              <span className="text-muted-foreground"> · ₹{latest.current_version?.total_amount ?? latest.total_amount ?? "—"}</span>
            </div>
            <div className="flex gap-2">
              <Button asChild variant="outline" size="sm"><Link to={`/quotations/${latest.id}`}>Open</Link></Button>
              {latest.status === "DRAFT" ? <Button asChild size="sm" className="bg-[#2563EB] hover:bg-[#1D4ED8]"><Link to={`/quotations/${latest.id}`}>Submit</Link></Button> : null}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
