// Status badge with per-status colors for Lead / Task / Quotation / Meeting
// workflow states. Unknown statuses fall back to a neutral badge.

import { cn } from "@/lib/utils";

const STATUS_DOTS = {
  ACTIVE: "bg-success",
  CONVERTED: "bg-success",
  ACCEPTED: "bg-success",
  APPROVED: "bg-success",
  LOST: "bg-error",
  REJECTED: "bg-error",
  PENDING: "bg-warning",
  PENDING_APPROVAL: "bg-warning",
  DRAFT: "bg-info",
  SENT: "bg-primary",
  REVISED: "bg-tertiary",
};

const STATUS_CLASSES = {
  ACTIVE: "bg-success-soft text-[#2E8B57] border-success-border",
  LOST: "bg-error-container text-error border-transparent",
  CONVERTED: "bg-success-soft text-success border-success-border",
  DRAFT: "bg-surface-container text-on-surface border-outline-variant",
  PENDING_APPROVAL: "bg-warning-soft text-warning border-warning-border",
  APPROVED: "bg-success-soft text-success border-success-border",
  SENT: "bg-info-soft text-info border-info-border",
  ACCEPTED: "bg-success-soft text-success border-success-border",
  REJECTED: "bg-error-container text-error border-transparent",
  REVISED: "bg-tertiary-soft text-tertiary border-transparent",
  PENDING: "bg-warning-soft text-warning border-warning-border",
};

export default function StatusBadge({ status, className }) {
  if (!status) return null;
  const dot = STATUS_DOTS[status] || "bg-primary";
  const label = String(status).replaceAll("_", " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium", STATUS_CLASSES[status] || "bg-surface-container text-on-surface border-outline-variant", className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
      {label}
    </span>
  );
}
