// G7 WORKAROUND — same caveat as the other master-data modules: verify IDs
// in Django admin until backend master-data endpoints ship.

export const REMINDER_TYPES = [
  { id: 1, name: "General" },
  { id: 2, name: "Call" },
  { id: 3, name: "Meeting" },
];

export const REMINDER_STATUSES = [
  { id: 1, name: "Active" },
  { id: 2, name: "Sent" },
];

const index = (rows) => Object.fromEntries(rows.map((row) => [row.id, row.name]));
const TYPE_NAMES = index(REMINDER_TYPES);
const STATUS_NAMES = index(REMINDER_STATUSES);

export const reminderTypeName = (id) => TYPE_NAMES[id] ?? (id ? `#${id}` : null);
export const reminderStatusName = (id) => STATUS_NAMES[id] ?? (id ? `#${id}` : null);
