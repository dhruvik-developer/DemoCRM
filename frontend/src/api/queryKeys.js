// Centralized TanStack Query key factory. Mutations invalidate by these
// prefixes so lists/details stay consistent (implementation plan Phase 2.7).

export const authKeys = {
  all: ["auth"],
  profile: (userId) => ["auth", "profile", userId],
};

export const leadKeys = {
  all: ["leads"],
  list: (filters) => ["leads", "list", filters ?? {}],
  detail: (leadId) => ["leads", "detail", leadId],
};

export const customerKeys = {
  all: ["customers"],
  list: (filters) => ["customers", "list", filters ?? {}],
  detail: (customerId) => ["customers", "detail", customerId],
  activities: (customerId) => ["customers", "activities", customerId],
  smartLookup: (params) => ["customers", "smart-lookup", params ?? {}],
};

export const crmKeys = {
  leadSources: ["crm", "lead-sources"],
  pipelines: ["crm", "pipelines"],
  pipelineStages: (pipelineId) => ["crm", "pipeline-stages", pipelineId ?? null],
  accounts: ["crm", "accounts"],
  contacts: ["crm", "contacts"],
  activities: (filters) => ["crm", "activities", filters ?? {}],
  auditLogs: (filters) => ["crm", "audit-logs", filters ?? {}],
};

export const quotationKeys = {
  all: ["quotations"],
  list: (filters) => ["quotations", "list", filters ?? {}],
  detail: (quotationId) => ["quotations", "detail", quotationId],
  events: ["quotations", "events"],
};

export const taskKeys = {
  all: ["tasks"],
  list: (filters) => ["tasks", "list", filters ?? {}],
  detail: (taskId) => ["tasks", "detail", taskId],
};

export const meetingKeys = {
  all: ["meetings"],
  detail: (meetingId) => ["meetings", "detail", meetingId],
};

export const reminderKeys = {
  all: ["reminders"],
  detail: (reminderId) => ["reminders", "detail", reminderId],
};

export const followUpKeys = {
  all: ["followups"],
  list: (filters) => ["followups", "list", filters ?? {}],
  detail: (followUpId) => ["followups", "detail", followUpId],
};

export const notificationKeys = {
  all: ["notifications"],
  inbox: (filters) => ["notifications", "inbox", filters ?? {}],
  templates: (filters) => ["notifications", "templates", filters ?? {}],
};

export const callFormKeys = {
  templates: (filters) => ["callforms", "templates", filters ?? {}],
  template: (templateId) => ["callforms", "templates", templateId],
  versions: (filters) => ["callforms", "versions", filters ?? {}],
  version: (versionId) => ["callforms", "versions", versionId],
  fields: (filters) => ["callforms", "fields", filters ?? {}],
  stageActivities: (stageId) => ["callforms", "stage-activities", stageId ?? null],
  leadPrimaryForm: (leadId) => ["callforms", "lead-primary-form", leadId],
  attempts: (leadId) => ["callforms", "attempts", leadId ?? null],
  submissions: (leadId) => ["callforms", "submissions", leadId ?? null],
  timeline: (leadId) => ["callforms", "timeline", leadId ?? null],
  analytics: (versionId) => ["callforms", "analytics", versionId ?? null],
  triggerRules: (versionId) => ["callforms", "trigger-rules", versionId ?? null],
  adhocProposals: (filters) => ["callforms", "adhoc-proposals", filters ?? {}],
};
