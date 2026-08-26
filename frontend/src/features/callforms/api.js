// CallForms API — router endpoints verified in frontend/docs/API_CONTRACT.md.
// Lists return PLAIN ARRAYS (no pagination class on these viewsets).

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

const unwrap = (data) => (Array.isArray(data) ? data : (data?.results ?? []));

// ── Templates ──────────────────────────────────────────────
export const getCallTemplates = async (params) =>
  unwrap((await apiClient.get(endpoints.callforms.templates, { params })).data);
export const getCallTemplate = async (id) =>
  (await apiClient.get(endpoints.callforms.templateDetail(id))).data;
export const createCallTemplate = async (values) =>
  (await apiClient.post(endpoints.callforms.templates, values)).data;
export const updateCallTemplate = async (id, partial) =>
  (await apiClient.patch(endpoints.callforms.templateDetail(id), partial)).data;
export const deleteCallTemplate = async (id) =>
  (await apiClient.delete(endpoints.callforms.templateDetail(id))).data;
export const setPrimaryVersion = async (templateId, versionId) =>
  (
    await apiClient.post(endpoints.callforms.templateSetPrimary(templateId), {
      version_id: versionId,
    })
  ).data;
export const createTemplateVersion = async (templateId, payload) =>
  (
    await apiClient.post(endpoints.callforms.templateCreateVersion(templateId), payload)
  ).data;

// ── Versions ───────────────────────────────────────────────
export const getVersions = async (params) =>
  unwrap((await apiClient.get(endpoints.callforms.versions, { params })).data);
export const getVersion = async (id) =>
  (await apiClient.get(endpoints.callforms.versionDetail(id))).data;
export const cloneVersion = async (versionId, payload) =>
  (await apiClient.post(endpoints.callforms.versionClone(versionId), payload)).data;

// ── Fields ─────────────────────────────────────────────────
export const getFields = async (params) =>
  unwrap((await apiClient.get(endpoints.callforms.fields, { params })).data);
export const createField = async (values) =>
  (await apiClient.post(endpoints.callforms.fields, values)).data;
export const updateField = async (fieldId, partial) =>
  (await apiClient.patch(endpoints.callforms.fieldDetail(fieldId), partial)).data;
export const deleteField = async (fieldId) =>
  (await apiClient.delete(endpoints.callforms.fieldDetail(fieldId))).data;
export const reorderFields = async (templateVersionId, orders) =>
  (
    await apiClient.post(endpoints.callforms.fieldsReorder, {
      template_version_id: templateVersionId,
      orders,
    })
  ).data;

// ── Stage activities ───────────────────────────────────────
export const getStageActivities = async () => unwrap(
  (await apiClient.get(endpoints.callforms.stageActivities)).data,
);
export const getStageActivitiesForStage = async (stageId) =>
  (
    await apiClient.get(endpoints.callforms.stageActivitiesForStage, {
      params: { stage_id: stageId },
    })
  ).data;
export const getLeadPrimaryForm = async (leadId) =>
  (
    await apiClient.get(endpoints.callforms.leadPrimaryForm, {
      params: { lead_id: leadId },
    })
  ).data;

// ── Attempts / Submissions ────────────────────────────────
export const logCallAttempt = async (values) =>
  (await apiClient.post(endpoints.callforms.attempts, values)).data;
export const getAttemptHistory = async (leadId) =>
  (
    await apiClient.get(endpoints.callforms.attemptLeadHistory, {
      params: { lead_id: leadId },
    })
  ).data;
export const submitForm = async (values) =>
  (await apiClient.post(endpoints.callforms.submissions, values)).data;
export const getLeadTimeline = async (params) =>
  (
    await apiClient.get(endpoints.callforms.submissionsLeadTimeline, { params })
  ).data;
export const getSubmissionAnalytics = async (templateVersionId) =>
  (
    await apiClient.get(endpoints.callforms.submissionsAnalytics, {
      params: { template_version_id: templateVersionId },
    })
  ).data;

// ── Trigger rules / Adhoc proposals ───────────────────────
export const getTriggerRules = async (params) =>
  unwrap((await apiClient.get(endpoints.callforms.triggerRules, { params })).data);
export const createTriggerRule = async (values) =>
  (await apiClient.post(endpoints.callforms.triggerRules, values)).data;
export const deleteTriggerRule = async (ruleId) =>
  (await apiClient.delete(endpoints.callforms.triggerRuleDetail(ruleId))).data;

export const getAdhocProposals = async () => unwrap(
  (await apiClient.get(endpoints.callforms.adhocProposals)).data,
);
export const createAdhocProposal = async (values) =>
  (await apiClient.post(endpoints.callforms.adhocProposals, values)).data;
export const reviewAdhocProposal = async (proposalId, payload) =>
  (
    await apiClient.post(endpoints.callforms.adhocProposalReview(proposalId), payload)
  ).data;
