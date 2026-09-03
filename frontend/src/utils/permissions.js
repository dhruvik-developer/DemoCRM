// Permission helpers built against frontend/docs/PERMISSION_CONTRACT.md.
//
// Backend reality (verified 2026-08-26):
// - Only Admin can call GET /roles/, so Manager/Employee permissions cannot be
//   fetched from the API. The seed maps below mirror accounts/signals.py and
//   are the fallback grant set for non-Admin roles.
// - A user with no role is denied everything server-side; we deny client-side
//   too. Superusers bypass everything.

export const ROLES = {
  ADMIN: "Admin",
  MANAGER: "Manager",
  EMPLOYEE: "Employee",
};

// Mirrors MANAGER_MODEL_PREFIXES + extras in backend/crm/accounts/signals.py.
// Synced 2026-08-31 to close G23 — adds customer_management core.
const MANAGER_MODEL_PREFIXES = [
  "task", "taskstatus", "taskpriority", "taskcategory",
  "meeting", "meetingstatus", "meetingtype", "meetingparticipant",
  "reminder", "remindertype", "reminderstatus",
  "followup", "followupnote", "followupstatus", "followuptypes",
  "notification", "notificationtemplate", "notificationtype",
  "calltemplate", "templateversion", "templatefield",
  "pipelinestageactivity", "callattempt", "formsubmission",
  "tasktriggerrule", "customeraccount", "customercontact", "customer",
  "adhocfieldproposal", "indexedsubmissionvalue",
  // customer_management core (G23 fix)
  "lead", "leadsource", "pipeline", "pipelinestage",
  "quotation", "quotationversion", "quotationlineitem", "quotationapproval",
  "payment",
  "activity", "auditlog",
];

const MANAGER_EXTRA_CODENAMES = [
  "assign_task", "send_notification",
  "manage_call_template", "manage_template_version", "manage_template_field",
  "manage_stage_activity", "add_adhoc_field", "manage_adhoc_field",
  // lead workflow (backend custom perms)
  "assign_lead", "progress_lead", "mark_lead_lost", "reengage_lead", "convert_lead", "record_payment",
  "view_quotation", "add_quotation", "change_quotation", "submit_quotation",
  "approve_quotation", "send_quotation", "request_quotation_revision",
  "accept_quotation", "reject_quotation",
  // pipeline management — required for /admin/pipelines (view_pipeline is via prefix, manage_* needed for POST/PATCH/DELETE)
  "manage_pipeline", "manage_pipeline_stage", "manage_lead_source",
];

// Mirrors EMPLOYEE_MODEL_PREFIXES + extras in accounts/signals.py.
// Synced 2026-08-31 to close G23 — adds customer_management core.
const EMPLOYEE_MODEL_PREFIXES = [
  "task", "taskstatus", "taskpriority", "taskcategory",
  "meeting", "meetingstatus", "meetingtype", "meetingparticipant",
  "reminder", "remindertype", "reminderstatus",
  "followup", "followupnote", "followupstatus", "followuptypes",
  "notification", "notificationtemplate", "notificationtype",
  "calltemplate", "templateversion", "templatefield",
  "pipelinestageactivity", "callattempt", "formsubmission",
  "tasktriggerrule", "customeraccount", "customercontact", "customer",
  "adhocfieldproposal", "indexedsubmissionvalue",
  // customer_management core (G23 fix) — auditlog stays Admin-only
  // NOTE: pipeline/pipelinestage removed — Employee must not see Pipeline nav (manager/admin only)
  "lead", "leadsource",
  "quotation", "quotationversion", "quotationlineitem", "quotationapproval",
  "activity",
];

const EMPLOYEE_EXTRA_CODENAMES = [
  "change_task", "add_meeting", "add_meetingparticipant",
  "delete_meetingparticipant", "add_reminder", "change_reminder",
  "delete_reminder", "add_followup", "add_followupnote",
  "change_notification", "add_callattempt", "change_callattempt",
  "add_formsubmission", "change_formsubmission", "add_adhoc_field",
  // Employee also needs change_followup (G13) not add_followup, plus workflow + quotation draft
  "change_followup", "change_followupstatus", "view_followup",
  "assign_lead", "progress_lead", "mark_lead_lost", "reengage_lead", "convert_lead",
  "add_quotation", "view_quotation", "change_quotation", "submit_quotation", "send_quotation", "request_quotation_revision",
];

const ACTIONS = ["view", "add", "change", "delete"];
const managerCodenames = new Set([
  ...MANAGER_MODEL_PREFIXES.flatMap((prefix) =>
    ACTIONS.map((action) => `${action}_${prefix}`),
  ),
  ...MANAGER_EXTRA_CODENAMES,
]);
const employeeCodenames = new Set([
  ...EMPLOYEE_MODEL_PREFIXES.map((prefix) => `view_${prefix}`),
  ...EMPLOYEE_EXTRA_CODENAMES,
]);

/**
 * Resolves the effective permission set for a user.
 *
 * `roleName` comes from auth resolution. Non-Admin users cannot read their
 * role's live grants from the API (GET /roles/ is Admin-only), so seeds are
 * used. If roleName is unknown (e.g. role id could not be resolved), the safe
 * default is the union of Manager+Employee seeds ("staff") so common modules
 * stay visible; anything not actually permitted still fails gracefully with a
 * handled 403.
 */
export function resolvePermissions({ roleName, isSuperuser = false }) {
  if (isSuperuser || roleName === ROLES.ADMIN) {
    return { isAdmin: true, roleName: ROLES.ADMIN, codenames: null }; // null = unrestricted
  }
  if (roleName === ROLES.MANAGER) {
    return { isAdmin: false, roleName: ROLES.MANAGER, codenames: managerCodenames };
  }
  if (roleName === ROLES.EMPLOYEE) {
    return { isAdmin: false, roleName: ROLES.EMPLOYEE, codenames: employeeCodenames };
  }
  return {
    isAdmin: false,
    roleName: roleName || null,
    codenames: new Set([...managerCodenames, ...employeeCodenames]),
  };
}

/** Checks a resolved set (see resolvePermissions). Null codenames = allow all. */
export function hasPermission(resolved, codename) {
  if (!resolved) return false;
  if (resolved.isAdmin) return true;
  return resolved.codenames.has(codename);
}
