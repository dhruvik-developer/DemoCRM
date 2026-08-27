// Real backend routes (verified against backend/crm/*/urls.py on 2026-08-26).
// VITE_API_BASE_URL already includes "/api", so every path here is a SUFFIX
// only — never prefix with /api (double-prefix bug, see frontend/docs/BACKEND_GAPS.md G14).

export const endpoints = {
  auth: {
    register: "/register/",
    login: "/login/",
    logout: "/logout/",
    refresh: "/refresh/",
    changePassword: "/change-password/",
    profile: (userId) => `/profile/${userId}/`,
    forgotPassword: "/forgot-password/",
    resetPassword: "/reset-password/",
    roles: "/roles/",
    roleDetail: (roleId) => `/roles/${roleId}/`,
    users: "/users/",
    unlockUser: (userId) => `/users/${userId}/unlock/`,
    permissions: "/permissions/",
    permissionDetail: (permissionId) => `/permissions/${permissionId}/`,
    assignRole: (userId) => `/assign-role/${userId}/`,
  },

  crm: {
    leadSources: "/crm/lead-sources/",
    pipelines: "/crm/pipelines/",
    pipelineStages: "/crm/pipeline-stages/",

    leads: "/crm/leads/",
    leadDetail: (leadId) => `/crm/leads/${leadId}/`,
    leadAssign: (leadId) => `/crm/leads/${leadId}/assign/`,
    leadProgress: (leadId) => `/crm/leads/${leadId}/progress/`,
    leadLost: (leadId) => `/crm/leads/${leadId}/lost/`,
    leadReengage: (leadId) => `/crm/leads/${leadId}/reengage/`,
    leadConvert: (leadId) => `/crm/leads/${leadId}/convert/`,

    activities: "/crm/activities/",
    auditLogs: "/crm/audit-logs/",

    customers: "/crm/customers/",
    customerDetail: (customerId) => `/crm/customers/${customerId}/`,
    customerActivities: (customerId) => `/crm/customers/${customerId}/activities/`,
    customerSmartLookup: "/crm/customers/smart-lookup/",

    accounts: "/crm/accounts/",
    contacts: "/crm/contacts/",

    quotations: "/crm/quotations/",
    quotationDetail: (quotationId) => `/crm/quotations/${quotationId}/`,
    quotationPdf: (quotationId) => `/crm/quotations/${quotationId}/pdf/`,
    quotationUpdateDraft: (quotationId) => `/crm/quotations/${quotationId}/update-draft/`,
    quotationSubmit: (quotationId) => `/crm/quotations/${quotationId}/submit/`,
    quotationApprove: (quotationId) => `/crm/quotations/${quotationId}/approve/`,
    quotationRejectApproval: (quotationId) =>
      `/crm/quotations/${quotationId}/reject-approval/`,
    quotationSend: (quotationId) => `/crm/quotations/${quotationId}/send/`,
    quotationSendEmail: (quotationId) => `/crm/quotations/${quotationId}/send-email/`,
    quotationRevision: (quotationId) => `/crm/quotations/${quotationId}/revision/`,
    quotationAccept: (quotationId) => `/crm/quotations/${quotationId}/accept/`,
    quotationReject: (quotationId) => `/crm/quotations/${quotationId}/reject/`,
    quotationEvents: "/crm/quotation-events/",
  },

  tasks: {
    list: "/tasks/",
    detail: (taskId) => `/tasks/${taskId}/`,
    assign: (taskId) => `/tasks/${taskId}/assign/`,
    status: (taskId) => `/tasks/${taskId}/status/`,
  },

  meetings: {
    // NOTE: no GET list endpoint exists yet (BACKEND_GAPS.md G8).
    // Lists are derived client-side from tasks until the backend ships one.
    create: "/tasks/meetings/",
    detail: (meetingId) => `/tasks/meetings/${meetingId}/`,
    approval: (meetingId) => `/tasks/meetings/${meetingId}/approval/`,
    reschedule: (meetingId) => `/tasks/meetings/${meetingId}/reschedule/`,
    status: (meetingId) => `/tasks/meetings/${meetingId}/status/`,
    participants: (meetingId) => `/tasks/meetings/${meetingId}/participants/`,
    participantDetail: (meetingId, userId) =>
      `/tasks/meetings/${meetingId}/participants/${userId}/`,
  },

  reminders: {
    // NOTE: no GET list endpoint exists yet (BACKEND_GAPS.md G8).
    create: "/tasks/reminders/",
    detail: (reminderId) => `/tasks/reminders/${reminderId}/`,
    status: (reminderId) => `/tasks/reminders/${reminderId}/status/`,
  },

  followups: {
    list: "/followups/",
    detail: (followupId) => `/followups/${followupId}/`,
    status: (followupId) => `/followups/${followupId}/status/`,
  },

  notifications: {
    templates: "/notification-templates/",
    templateDetail: (templateId) => `/notification-templates/${templateId}/`,
    send: "/notifications/send/",
    list: "/notifications/",
    detail: (notificationId) => `/notifications/${notificationId}/`,
    markRead: (notificationId) => `/notifications/${notificationId}/read/`,
  },

  callforms: {
    templates: "/callforms/templates/",
    templateDetail: (templateId) => `/callforms/templates/${templateId}/`,
    templateSetPrimary: (templateId) => `/callforms/templates/${templateId}/set-primary/`,
    templateCreateVersion: (templateId) =>
      `/callforms/templates/${templateId}/create-version/`,

    versions: "/callforms/versions/",
    versionDetail: (versionId) => `/callforms/versions/${versionId}/`,
    versionClone: (versionId) => `/callforms/versions/${versionId}/clone/`,

    fields: "/callforms/fields/",
    fieldDetail: (fieldId) => `/callforms/fields/${fieldId}/`,
    fieldsReorder: "/callforms/fields/reorder/",

    stageActivities: "/callforms/stage-activities/",
    stageActivityDetail: (stageActivityId) =>
      `/callforms/stage-activities/${stageActivityId}/`,
    stageActivitySetPrimary: (stageActivityId) =>
      `/callforms/stage-activities/${stageActivityId}/set-primary/`,
    stageActivitiesForStage: "/callforms/stage-activities/for-stage/",
    leadPrimaryForm: "/callforms/stage-activities/lead-primary-form/",

    attempts: "/callforms/attempts/",
    attemptDetail: (attemptId) => `/callforms/attempts/${attemptId}/`,
    attemptLeadHistory: "/callforms/attempts/lead-history/",

    submissions: "/callforms/submissions/",
    submissionDetail: (submissionId) => `/callforms/submissions/${submissionId}/`,
    submissionsLeadTimeline: "/callforms/submissions/lead-timeline/",
    submissionsAnalytics: "/callforms/submissions/analytics/",

    triggerRules: "/callforms/trigger-rules/",
    triggerRuleDetail: (ruleId) => `/callforms/trigger-rules/${ruleId}/`,

    adhocProposals: "/callforms/adhoc-proposals/",
    adhocProposalDetail: (proposalId) => `/callforms/adhoc-proposals/${proposalId}/`,
    adhocProposalReview: (proposalId) =>
      `/callforms/adhoc-proposals/${proposalId}/review/`,

    indexedValues: "/callforms/indexed-values/",
  },
};
