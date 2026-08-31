// G7 WORKAROUND (frontend/docs/BACKEND_GAPS.md): TaskStatus / TaskPriority /
// TaskCategory have NO REST endpoints yet — rows exist only in the database
// (managed via Django admin). These constants hardcode the conventional IDs.
//
// ⚠️ VERIFY these IDs against your database (Django admin → Task statuses /
// priorities / categories) before relying on them. When the backend ships
// master-data endpoints, replace this module with queries and delete this
// comment alongside the BACKEND_GAPS.md G7 entry.

export const TASK_STATUSES = [
  { id: 1, name: "Pending" },
  { id: 2, name: "In Progress" },
  { id: 3, name: "Completed" },
  { id: 4, name: "Cancelled" },
];

export const TASK_PRIORITIES = [
  { id: 1, name: "Low" },
  { id: 2, name: "Medium" },
  { id: 3, name: "High" },
];

export const TASK_CATEGORIES = [
  { id: 1, name: "Follow-Up" },
  { id: 2, name: "General" },
];

const index = (rows) =>
  Object.fromEntries(rows.map((row) => [row.id, row.name]));

const STATUS_NAMES = index(TASK_STATUSES);
const PRIORITY_NAMES = index(TASK_PRIORITIES);
const CATEGORY_NAMES = index(TASK_CATEGORIES);

export const taskStatusName = (id) => STATUS_NAMES[id] ?? (id ? `#${id}` : null);
export const taskPriorityName = (id) => PRIORITY_NAMES[id] ?? (id ? `#${id}` : null);
export const taskCategoryName = (id) => CATEGORY_NAMES[id] ?? (id ? `#${id}` : null);
