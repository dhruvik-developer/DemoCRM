import { Check } from "lucide-react";

export default function PipelineStepper({ stages = [], currentStageId, stageEnteredAt }) {
  if (!stages.length) return null;
  const sorted = [...stages].sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
  const currentIndex = sorted.findIndex((s) => s.id === currentStageId);
  const activeIndex = currentIndex === -1 ? 0 : currentIndex;

  return (
    <div className="flex items-center gap-0 overflow-x-auto py-3">
      {sorted.map((stage, idx) => {
        const isCompleted = idx < activeIndex;
        const isActive = idx === activeIndex;
        // eslint-disable-next-line react-hooks/purity
        const daysInStage = isActive && stageEnteredAt ? Math.floor((Date.now() - new Date(stageEnteredAt).getTime()) / 86400000) : null;

        return (
          <div key={stage.id} className="flex items-center gap-0 flex-1 min-w-0">
            <div className="flex flex-col items-center gap-1.5 min-w-[96px] flex-1 relative">
              <div
                className={[
                  "flex h-[26px] w-[26px] items-center justify-center rounded-full text-[11px] font-bold border-2 transition-all duration-200 z-10",
                  isActive
                    ? "bg-[#2563EB] border-[#2563EB] text-white shadow-[0_0_0_4px_#EEF2FF]"
                    : isCompleted
                      ? "bg-[#10B981] border-[#10B981] text-white"
                      : "bg-white border-[#E5E7EB] text-muted-foreground",
                ].join(" ")}
                aria-label={`${stage.name} ${isActive ? "active" : isCompleted ? "completed" : "pending"}`}
              >
                {isCompleted ? <Check className="h-3.5 w-3.5" /> : idx + 1}
              </div>
              <span
                className={[
                  "text-[11.5px] font-semibold text-center leading-tight line-clamp-2",
                  isActive ? "text-foreground font-extrabold" : isCompleted ? "text-foreground" : "text-muted-foreground",
                ].join(" ")}
              >
                {stage.name}
              </span>
              {stage.requires_quotation ? (
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                  Quotation
                </span>
              ) : null}
              {isActive && daysInStage !== null ? (
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${daysInStage > 7 ? "bg-red-50 text-red-700 border-red-200" : "bg-muted text-muted-foreground"}`}>
                  {daysInStage}d {daysInStage > 7 ? "⚠️" : ""}
                </span>
              ) : null}
            </div>
            {idx < sorted.length - 1 ? (
              <div
                className={[
                  "h-0.5 flex-1 mx-1 rounded -mt-6",
                  idx < activeIndex ? "bg-[#10B981]" : "bg-[#E5E7EB]",
                ].join(" ")}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
