import { useActivities } from "@/features/activities/hooks";
import { useLeadTimeline } from "@/features/callforms/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Phone, FileText, CheckSquare } from "lucide-react";

function TimelineDot({ type }) {
  const bg = type === "submission" ? "bg-[#2563EB] text-white" : type === "followup" ? "bg-amber-500 text-white" : "bg-muted";
  return (
    <div className={`flex h-7 w-7 items-center justify-center rounded-full border bg-white ${bg}`}>
      {type === "submission" ? <FileText className="h-3.5 w-3.5" /> : type === "followup" ? <CheckSquare className="h-3.5 w-3.5" /> : <Phone className="h-3.5 w-3.5" />}
    </div>
  );
}

export default function SalesTimeline({ leadId }) {
  const activitiesQ = useActivities(leadId ? { lead: leadId } : undefined);
  const timelineQ = useLeadTimeline({ lead_id: leadId });

  const activities = (activitiesQ.data ?? []).map((a) => ({ kind: "activity", at: a.created_at, data: a }));
  const submissions = (Array.isArray(timelineQ.data) ? timelineQ.data : timelineQ.data?.results ?? []).map((s) => ({ kind: "submission", at: s.submitted_at ?? s.created_at, data: s }));

  const merged = [...activities, ...submissions].sort((a, b) => new Date(b.at) - new Date(a.at)).slice(0, 20);

  if (activitiesQ.isLoading || timelineQ.isLoading) return <Card className="rounded-xl"><CardContent className="p-4 text-sm text-muted-foreground">Loading timeline…</CardContent></Card>;
  if (!merged.length) return <Card className="rounded-xl border-dashed"><CardHeader className="pb-2"><CardTitle className="text-sm">Activity / Call timeline</CardTitle></CardHeader><CardContent><p className="text-sm text-muted-foreground">No calls or activities yet. Log an activity or fill the stage form — it will appear here.</p></CardContent></Card>;

  return (
    <Card className="rounded-xl">
      <CardHeader className="pb-3"><CardTitle className="text-sm">Activity / Call timeline</CardTitle></CardHeader>
      <CardContent className="flex flex-col gap-0">
        <div className="relative pl-6">
          <div className="absolute left-3 top-1 bottom-1 w-0.5 bg-[#E5E7EB]" />
          {merged.map((item, idx) => (
            <div key={`${item.kind}-${idx}`} className="relative flex gap-3 pb-4 last:pb-0">
              <div className="absolute left-[-18px] top-0"><TimelineDot type={item.kind} /></div>
              <div className="flex-1 rounded-lg border bg-card p-3">
                {item.kind === "activity" ? (
                  <>
                    <div className="flex items-center gap-2"><Badge variant="outline">{item.data.activity_type}</Badge><span className="text-sm font-medium">{item.data.outcome}</span></div>
                    {item.data.notes ? <p className="mt-1 text-sm text-muted-foreground">{item.data.notes}</p> : null}
                    <span className="text-xs text-muted-foreground">{item.at ? new Date(item.at).toLocaleString() : ""}</span>
                  </>
                ) : (
                  <>
                    <div className="flex items-center gap-2"><Badge className="bg-[#2563EB] text-white">Form submission</Badge><span className="text-sm font-medium">{item.data.template_name ?? "Submission"}</span></div>
                    <div className="mt-1 grid gap-0.5 text-xs text-muted-foreground">
                      {item.data.data ? Object.entries(item.data.data).slice(0,3).map(([k,v]) => <span key={k}>{k}: {String(v).slice(0,60)}</span>) : null}
                    </div>
                    <span className="text-xs text-muted-foreground">{item.at ? new Date(item.at).toLocaleString() : ""}</span>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
