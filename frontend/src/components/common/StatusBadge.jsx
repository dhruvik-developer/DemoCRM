// Status badge with per-status colors for Lead / Task / Quotation / Meeting
// workflow states. Unknown statuses fall back to a neutral badge.

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const STATUS_CLASSES = {
  // Leads
  ACTIVE: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  LOST: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  CONVERTED: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
  // Quotations
  DRAFT: "bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-300",
  PENDING_APPROVAL: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  APPROVED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  SENT: "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300",
  ACCEPTED: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
  REJECTED: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  REVISED: "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300",
  // Meetings
  PENDING: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
};

export default function StatusBadge({ status, className }) {
  if (!status) return null;
  return (
    <Badge variant="outline" className={cn(STATUS_CLASSES[status], className)}>
      {String(status).replaceAll("_", " ").toLowerCase()}
    </Badge>
  );
}
