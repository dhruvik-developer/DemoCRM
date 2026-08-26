// G7 WORKAROUND (frontend/docs/BACKEND_GAPS.md): FollowUpStatus /
// FollowUpTypes and ReminderType / ReminderStatus exist only in the database
// (Django admin) — no REST endpoints yet. VERIFY IDs before relying on them.

export const FOLLOWUP_STATUSES = [
  { id: 1, name: "Pending" },
  { id: 2, name: "Completed" },
];

export const FOLLOWUP_TYPES = [
  { id: 1, name: "Call" },
  { id: 2, name: "Email" },
  { id: 3, name: "Meeting" },
];

const index = (rows) => Object.fromEntries(rows.map((row) => [row.id, row.name]));
const STATUS_NAMES = index(FOLLOWUP_STATUSES);
const TYPE_NAMES = index(FOLLOWUP_TYPES);

export const followUpStatusName = (id) => STATUS_NAMES[id] ?? (id ? `#${id}` : null);
export const followUpTypeName = (id) => TYPE_NAMES[id] ?? (id ? `#${id}` : null);
