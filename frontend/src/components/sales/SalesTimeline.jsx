import { useActivities } from "@/features/activities/hooks";
import { useLeadTimeline } from "@/features/callforms/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Phone, FileText, CheckSquare } from "lucide-react";

function TimelineDot({ type }) {
  const bg = type === "submission" ? "bg-primary-soft text-primary border-transparent" : type === "followup" ? "bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]" : "bg-surface-container text-muted-foreground border-outline-variant";
  return (
    <div className={`flex h-8 w-8 items-center justify-center rounded-full border shadow-sm ${bg}`}>
      {type === "submission" ? <FileText className="h-4 w-4" /> : type === "followup" ? <CheckSquare className="h-4 w-4" /> : <Phone className="h-4 w-4" />}
    </div>
  );
}

export default function SalesTimeline({ leadId }) {
  const activitiesQ = useActivities(leadId ? { lead: leadId } : undefined);
  const timelineQ = useLeadTimeline({ lead_id: leadId });

  const activities = (activitiesQ.data ?? []).map((a) => ({ kind: "activity", at: a.created_at, data: a }));
  const submissions = (Array.isArray(timelineQ.data) ? timelineQ.data : timelineQ.data?.results ?? []).map((s) => ({ kind: "submission", at: s.submitted_at ?? s.created_at, data: s }));

  const merged = [...activities, ...submissions].sort((a, b) => new Date(b.at) - new Date(a.at)).slice(0, 20);

  if (activitiesQ.isLoading || timelineQ.isLoading) return <Card className="rounded-[16px] border-outline"><CardContent className="p-4 text-sm text-muted-foreground">Loading timeline…</CardContent></Card>;
  if (!merged.length) return <Card className="rounded-[16px] border-dashed border-outline"><CardHeader className="pb-2"><CardTitle className="text-sm">Activity / Call timeline</CardTitle></CardHeader><CardContent><p className="text-sm text-muted-foreground">No calls or activities yet. Log an activity or fill the stage form — it will appear here.</p></CardContent></Card>;

  return (
    <Card className="rounded-[16px] border-outline bg-surface shadow-sm">
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-bold">Activity & Communication Feed</CardTitle>
        <span className="text-[11px] text-muted-foreground font-medium">{merged.length} events</span>
      </CardHeader>
      <CardContent className="flex flex-col gap-0">
        <div className="relative max-h-[480px] overflow-y-auto pl-8 pr-1">
          <div className="absolute left-[15px] top-2 bottom-2 w-[2px] bg-outline-variant" />
          {merged.map((item, idx) => (
            <div key={`${item.kind}-${idx}`} className="relative flex gap-3 pb-4 last:pb-0">
              <div className="absolute left-[-20px] top-0 z-10"><TimelineDot type={item.kind} /></div>
              <div className="flex-1 rounded-lg border border-outline bg-card p-3 shadow-sm">
                {item.kind === "activity" ? (
                  <>
                    <div className="flex items-center gap-2"><Badge variant="outline" className="text-[11px]">{item.data.activity_type}</Badge><span className="text-[12px] font-bold">{item.data.outcome}</span></div>
                    {item.data.notes ? <p className="mt-1 text-[12px] leading-[1.4] text-muted-foreground">{item.data.notes}</p> : null}
                    <span className="mt-1 block text-[10.5px] text-muted-foreground">{item.at ? new Date(item.at).toLocaleString() : ""}</span>
                  </>
                ) : (
                  <>
                    <div className="flex items-center gap-2"><Badge className="bg-secondary text-white text-[11px]">Form submission</Badge><span className="text-[12px] font-bold">{item.data.template_name ?? "Submission"}</span></div>
                    <div className="mt-1 grid gap-0.5 text-[11px] text-muted-foreground">
                      {item.data.data ? Object.entries(item.data.data).slice(0,3).map(([k,v]) => <span key={k} className="truncate">{k}: {String(v).slice(0,60)}</span>) : null}
                    </div>
                    <span className="mt-1 block text-[10.5px] text-muted-foreground">{item.at ? new Date(item.at).toLocaleString() : ""}</span>
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
