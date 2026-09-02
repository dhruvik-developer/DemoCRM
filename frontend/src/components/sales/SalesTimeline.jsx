import { useActivities } from "@/features/activities/hooks";
import { useLeadTimeline } from "@/features/callforms/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Phone, FileText, CheckSquare } from "lucide-react";

function TimelineDot({ type }) {
  const bg = type === "submission" ? "bg-[#EEF2FF] text-[#4F46E5] border-[#C7D2FE]" : type === "followup" ? "bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]" : "bg-[#F1F5F9] text-muted-foreground border-[#E2E8F0]";
  return (
    <div className={`flex h-7 w-7 items-center justify-center rounded-full border shadow-sm ${bg}`}>
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
    <Card className="rounded-[14px] border-[#E2E8F0] shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-bold">Activity & Communication Feed</CardTitle>
        <span className="text-[11px] text-muted-foreground font-medium">{merged.length} events</span>
      </CardHeader>
      <CardContent className="flex flex-col gap-0">
        <div className="relative pl-6">
          <div className="absolute left-[13px] top-2 bottom-2 w-0.5 bg-[#E2E8F0]" />
          {merged.map((item, idx) => (
            <div key={`${item.kind}-${idx}`} className="relative flex gap-3 pb-4 last:pb-0">
              <div className="absolute left-[-18px] top-0 z-10"><TimelineDot type={item.kind} /></div>
              <div className="flex-1 rounded-lg border border-[#E2E8F0] bg-card p-3 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
                {item.kind === "activity" ? (
                  <>
                    <div className="flex items-center gap-2"><Badge variant="outline" className="text-[11px]">{item.data.activity_type}</Badge><span className="text-[12px] font-bold">{item.data.outcome}</span></div>
                    {item.data.notes ? <p className="mt-1 text-[12px] leading-[1.4] text-muted-foreground">{item.data.notes}</p> : null}
                    <span className="mt-1 block text-[10.5px] text-muted-foreground">{item.at ? new Date(item.at).toLocaleString() : ""}</span>
                  </>
                ) : (
                  <>
                    <div className="flex items-center gap-2"><Badge className="bg-[#2563EB] text-white text-[11px]">Form submission</Badge><span className="text-[12px] font-bold">{item.data.template_name ?? "Submission"}</span></div>
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
