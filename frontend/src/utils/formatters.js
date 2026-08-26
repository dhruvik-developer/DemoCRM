// Shared display formatters.

export function toMoney(value) {
  return Number(value ?? 0).toFixed(2);
}

export function formatDateTime(value) {
  return value ? new Date(value).toLocaleString() : "—";
}

export function shortId(value) {
  return value ? `${String(value).slice(0, 8)}…` : null;
}
