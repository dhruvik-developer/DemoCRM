import { Check, Clock } from "lucide-react";

export default function PipelineStepper({ stages = [], currentStageId, stageEnteredAt }) {
  if (!stages.length) return null;
  const sorted = [...stages].sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
  const currentIndex = sorted.findIndex((s) => s.id === currentStageId);
  const activeIndex = currentIndex === -1 ? 0 : currentIndex;

  return (
    <div className="flex items-center gap-2 sm:gap-3 overflow-x-auto py-2.5 scrollbar-none">
      {sorted.map((stage, idx) => {
        const isCompleted = idx < activeIndex;
        const isActive = idx === activeIndex;
        // eslint-disable-next-line react-hooks/purity -- stageEnteredAt is a timestamp, days calc is idempotent per render
        const daysInStage = isActive && stageEnteredAt ? Math.floor((Date.now() - new Date(stageEnteredAt).getTime()) / 86400000) : null;

        return (
          <div key={stage.id} className="flex min-w-[130px] sm:min-w-0 flex-1 flex-col gap-1.5">
            {/* Progression Track Bar */}
            <div
              className={[
                "h-1.5 w-full rounded-full transition-all duration-300",
                isCompleted
                  ? "bg-primary"
                  : isActive
                    ? "bg-[#FF6A3D]"
                    : "bg-[var(--surface-container)] border border-border",
              ].join(" ")}
            />

            {/* Stage Indicator & Title */}
            <div className="flex items-center gap-2 mt-0.5">
              <span
                className={[
                  "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold border transition-colors",
                  isActive
                    ? "bg-[#FF6A3D] text-[#2B1206] border-[#FF6A3D] shadow-xs"
                    : isCompleted
                      ? "bg-primary text-white border-primary"
                      : "bg-surface border-border text-muted-foreground",
                ].join(" ")}
                aria-label={`${stage.name} ${isActive ? "active" : isCompleted ? "completed" : "upcoming"}`}
              >
                {isCompleted ? <Check className="h-3 w-3 stroke-[2.5]" /> : idx + 1}
              </span>
              <span
                className={[
                  "text-[12px] leading-tight truncate transition-colors",
                  isActive
                    ? "font-bold text-foreground"
                    : isCompleted
                      ? "font-semibold text-foreground"
                      : "text-muted-foreground dark:text-[#A4B8B0] font-medium",
                ].join(" ")}
              >
                {stage.name}
              </span>
              {isActive && daysInStage !== null ? (
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${daysInStage > 7 ? "bg-red-50 text-red-700 border-red-200" : "bg-muted text-muted-foreground"}`}>
                  {daysInStage}d {daysInStage > 7 ? "⚠️" : ""}
                </span>
              ) : null}
            </div>

            {/* Badges: Quotation Requirement or Days in Stage */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {stage.requires_quotation ? (
                <span className="inline-flex items-center gap-1 rounded-full border border-warning-border bg-warning-soft px-2 py-0.5 text-[10px] font-semibold text-warning">
                  <span className="h-1.5 w-1.5 rounded-full bg-warning" /> Quotation
                </span>
              ) : null}
              {isActive && daysInStage !== null ? (
                <span
                  className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-mono font-medium ${
                    daysInStage > 7
                      ? "bg-destructive/10 text-destructive border-destructive/20"
                      : "bg-primary-soft text-primary border-primary/20"
                  }`}
                >
                  <Clock className="h-2.5 w-2.5" />
                  {daysInStage}d {daysInStage > 7 ? "• slow" : ""}
                </span>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
