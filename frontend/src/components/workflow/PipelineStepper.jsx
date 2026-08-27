import { Check } from "lucide-react";

export default function PipelineStepper({ stages = [], currentStageId }) {
  if (!stages.length) return null;
  const sorted = [...stages].sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
  const currentIndex = sorted.findIndex((s) => s.id === currentStageId);
  const activeIndex = currentIndex === -1 ? 0 : currentIndex;

  return (
    <div className="flex items-center gap-0 overflow-x-auto py-2">
      {sorted.map((stage, idx) => {
        const isCompleted = idx < activeIndex;
        const isActive = idx === activeIndex;

        return (
          <div key={stage.id} className="flex items-center gap-0 flex-1 min-w-0">
            <div className="flex flex-col items-center gap-1.5 min-w-[96px] flex-1">
              <div
                className={[
                  "flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold border-2 transition-colors",
                  isActive
                    ? "bg-[#2563EB] border-[#2563EB] text-white"
                    : isCompleted
                      ? "bg-[#111214] border-[#111214] text-white"
                      : "bg-white border-[#E5E7EB] text-muted-foreground",
                ].join(" ")}
                aria-label={`${stage.name} ${isActive ? "active" : isCompleted ? "completed" : "pending"}`}
              >
                {isCompleted ? <Check className="h-3.5 w-3.5" /> : idx + 1}
              </div>
              <span
                className={[
                  "text-xs font-medium text-center leading-tight line-clamp-2",
                  isActive ? "text-foreground" : isCompleted ? "text-foreground" : "text-muted-foreground",
                ].join(" ")}
              >
                {stage.name}
              </span>
              {stage.requires_quotation ? (
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                  Quotation
                </span>
              ) : null}
            </div>
            {idx < sorted.length - 1 ? (
              <div
                className={[
                  "h-0.5 flex-1 mx-1 rounded",
                  idx < activeIndex ? "bg-[#111214]" : idx === activeIndex ? "bg-[#E5E7EB]" : "bg-[#E5E7EB]",
                ].join(" ")}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
