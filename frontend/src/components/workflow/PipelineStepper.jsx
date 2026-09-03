import { Check } from "lucide-react";

export default function PipelineStepper({ stages = [], currentStageId, stageEnteredAt }) {
  if (!stages.length) return null;
  const sorted = [...stages].sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
  const currentIndex = sorted.findIndex((s) => s.id === currentStageId);
  const activeIndex = currentIndex === -1 ? 0 : currentIndex;

  return (
    <div className="flex items-center gap-3 overflow-x-auto py-4">
      {sorted.map((stage, idx) => {
        const isCompleted = idx < activeIndex;
        const isActive = idx === activeIndex;
        // eslint-disable-next-line react-hooks/purity -- stageEnteredAt is a timestamp, days calc is idempotent per render
        const daysInStage = isActive && stageEnteredAt ? Math.floor((Date.now() - new Date(stageEnteredAt).getTime()) / 86400000) : null;

        return (
          <div key={stage.id} className="flex min-w-0 flex-1 flex-col gap-2">
            <div
              className={[
                "h-1.5 w-full rounded-full transition-colors",
                isCompleted ? "bg-primary" : isActive ? "bg-secondary" : "bg-surface-container",
              ].join(" ")}
            />
            <div className="flex items-center gap-2">
              <span
                className={[
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold border",
                  isActive ? "bg-secondary text-[#2B1206] border-secondary" : isCompleted ? "bg-primary text-white border-primary" : "bg-surface border-outline-variant text-on-surface-variant",
                ].join(" ")}
                aria-label={`${stage.name} ${isActive ? "active" : isCompleted ? "completed" : "upcoming"}`}
              >
                {isCompleted ? <Check className="h-3.5 w-3.5" /> : idx + 1}
              </span>
              <span className={["text-sm leading-tight line-clamp-1", isActive ? "font-semibold text-on-surface" : isCompleted ? "font-medium text-on-surface" : "text-on-surface-variant"].join(" ")}>
                {stage.name}
              </span>
            </div>
            {stage.requires_quotation ? (
              <span className="inline-flex w-fit items-center gap-1 rounded-full border border-warning-border bg-warning-soft px-2 py-0.5 text-xs font-medium text-warning">
                <span className="h-1.5 w-1.5 rounded-full bg-warning" /> Quotation
              </span>
            ) : null}
            {isActive && daysInStage !== null ? (
              <span className={`inline-flex w-fit rounded-full border px-2 py-0.5 text-xs font-mono ${daysInStage > 7 ? "bg-error-container text-error border-transparent" : "bg-surface-container text-on-surface-variant border-outline-variant"}`}>
                {daysInStage}d {daysInStage > 7 ? "• overdue" : ""}
              </span>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
