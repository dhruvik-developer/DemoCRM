import { useMemo } from "react";
import { hasPermission } from "@/utils/permissions";

/**
 * Derives UI capabilities for the sales workflow.
 * Backend remains authoritative — this is for button visibility only.
 * Mirrors CRM_FRONTEND_AGENT_MASTER_PROMPT.md §10
 */
export function useWorkflowCapabilities({
  lead,
  stages = [],
  currentStage,
  currentForm,
  permissions, // resolved from useAuth
  quotation, // current quotation for lead if any
}) {
  return useMemo(() => {
    if (!lead) return {};
    const status = lead.status;
    const isActive = status === "ACTIVE";
    const isLost = status === "LOST";
    const isConverted = status === "CONVERTED";

    const sorted = [...stages].sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
    const currentIndex = sorted.findIndex((s) => s.id === (currentStage?.id ?? lead.current_stage));
    const isFinalStage = currentIndex !== -1 && currentIndex === sorted.length - 1;
    const hasStages = sorted.length > 0;

    const requiresQuotation = Boolean(currentStage?.requires_quotation);
    const hasRequiredForm = Boolean(currentForm?.fields?.length);
    const formIsLocked = Boolean(currentForm?.is_locked);

    // Quotation states that block progress per backend
    const quotationBlocks = quotation && ["DRAFT", "PENDING_APPROVAL"].includes(quotation.status);

    const can = (codename) => hasPermission(permissions, codename);

    return {
      canAssign: isActive && can("assign_lead"),
      canProgress: isActive && can("progress_lead") && hasStages && !isFinalStage && !quotationBlocks,
      canMarkLost: isActive && can("mark_lead_lost"),
      canReengage: isLost && can("reengage_lead"),
      canConvert: isActive && can("convert_lead") && (!requiresQuotation || quotation?.status === "ACCEPTED"),
      canCreateQuotation: isActive && can("add_quotation"),
      requiresQuotation,
      hasRequiredForm,
      formIsLocked,
      isFinalStage,
      isActive,
      isLost,
      isConverted,
      currentIndex,
      nextStage: sorted[currentIndex + 1] ?? null,
    };
  }, [lead, stages, currentStage, currentForm, permissions, quotation]);
}
