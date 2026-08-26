// G7 WORKAROUND (frontend/docs/BACKEND_GAPS.md): MeetingStatus / MeetingType
// rows exist only in the database (Django admin) — no REST endpoints yet.
//
// Meeting TYPE ids are anchored by backend code: services use
// ONLINE_MEETING_TYPE_ID = 1 (offline assumed 2). STATUS ids follow the same
// AutoField seeding convention as tasks (Pending/Scheduled = 1) — VERIFY in
// Django admin. Replace this module when master-data endpoints ship.

export const MEETING_TYPES = [
  { id: 1, name: "Online" },
  { id: 2, name: "Offline" },
];

export const MEETING_STATUSES = [
  { id: 1, name: "Scheduled" },
  { id: 2, name: "Completed" },
  { id: 3, name: "Cancelled" },
];

const index = (rows) => Object.fromEntries(rows.map((row) => [row.id, row.name]));
const TYPE_NAMES = index(MEETING_TYPES);
const STATUS_NAMES = index(MEETING_STATUSES);

export const meetingTypeName = (id) => TYPE_NAMES[id] ?? (id ? `#${id}` : null);
export const meetingStatusName = (id) => STATUS_NAMES[id] ?? (id ? `#${id}` : null);
