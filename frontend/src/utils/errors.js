// Backend error shapes are NOT standardized (frontend/docs/BACKEND_GAPS.md G11):
//   {"detail": "..."}                      — DRF detail / custom business errors
//   {"field_name": ["msg", ...]}           — DRF serializer field errors
//   {"non_field_errors": ["msg"]}          — DRF object-level errors
//   {"error": "..."}                       — some views (Notification, etc.)
// normalizeApiError folds all of them into one predictable shape for forms/toasts.

function extractMessage(value) {
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(extractMessage).join(" ");
  }
  if (value && typeof value === "object") {
    return Object.values(value).map(extractMessage).join(" ");
  }
  return "";
}

/**
 * @param {Error} error - axios error (or anything with a .response)
 * @returns {{ message: string, fieldErrors: Record<string, string[]>, status: number }}
 */
export function normalizeApiError(error) {
  const status = error?.response?.status ?? 0;
  const data = error?.response?.data;
  const fieldErrors = {};
  let message;

  if (!data) {
    message = error?.message || "Network error — could not reach the server.";
  } else if (data.detail) {
    message = extractMessage(data.detail);
  } else if (data.error) {
    message = extractMessage(data.error);
  } else {
    for (const [key, value] of Object.entries(data)) {
      fieldErrors[key] = Array.isArray(value) ? value : [String(value)];
    }
    message =
      fieldErrors.non_field_errors?.join(" ") ||
      extractMessage(Object.values(fieldErrors)[0]) ||
      "Validation failed.";
  }

  return { message, fieldErrors, status };
}

/** Flat one-liner for toasts / alerts. */
export function getApiErrorMessage(error) {
  return normalizeApiError(error).message;
}
