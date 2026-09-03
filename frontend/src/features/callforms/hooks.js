// CallForms queries + mutations. Every mutation invalidates the whole
// callforms subtree — the module is small enough that granular keys aren't
// worth the bookkeeping yet (revisit if performance demands it).

import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { queryClient } from "@/api/queryClient";
import { getApiErrorMessage } from "@/utils/errors";
import * as api from "./api";

const invalidate = () => queryClient.invalidateQueries({ queryKey: ["callforms"] });

function useCallFormsMutation(mutationFn, successMessage) {
  return useMutation({
    mutationFn,
    onSuccess: async (result) => {
      invalidate();
      if (successMessage) toast.success(successMessage);
      return result;
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

// Templates
export const useCallTemplates = () =>
  useQuery({ queryKey: ["callforms", "templates"], queryFn: api.getCallTemplates });
export const useCallTemplate = (id) =>
  useQuery({
    queryKey: ["callforms", "templates", id],
    queryFn: () => api.getCallTemplate(id),
    enabled: Boolean(id),
  });
export const useCreateCallTemplate = () =>
  useCallFormsMutation(api.createCallTemplate, "Template created.");
export const useUpdateCallTemplate = () =>
  useCallFormsMutation(({ id, ...values }) => api.updateCallTemplate(id, values), "Template updated.");
export const useDeleteCallTemplate = () =>
  useCallFormsMutation((id) => api.deleteCallTemplate(id), "Template deleted.");

// Versions
export const useVersions = (templateId) =>
  useQuery({
    queryKey: ["callforms", "versions", templateId],
    queryFn: () => api.getVersions(templateId ? { template: templateId } : {}),
    enabled: Boolean(templateId),
  });
export const useCreateVersion = () =>
  useCallFormsMutation(
    ({ templateId, ...payload }) => api.createTemplateVersion(templateId, payload),
    "New version created.",
  );
export const useCloneVersion = () =>
  useCallFormsMutation(
    ({ versionId, ...payload }) => api.cloneVersion(versionId, payload),
    "Version cloned.",
  );
export const useSetPrimaryVersion = () =>
  useCallFormsMutation(
    ({ templateId, versionId }) => api.setPrimaryVersion(templateId, versionId),
    "Primary version set.",
  );

// Fields
export const useFields = (versionId) =>
  useQuery({
    queryKey: ["callforms", "fields", versionId],
    queryFn: () => api.getFields(versionId ? { template_version: versionId } : {}),
    enabled: Boolean(versionId),
  });
export const useCreateField = () =>
  useCallFormsMutation(api.createField, "Field added.");
export const useUpdateField = () =>
  useCallFormsMutation(({ fieldId, ...partial }) => api.updateField(fieldId, partial));
export const useDeleteField = () =>
  useCallFormsMutation((fieldId) => api.deleteField(fieldId), "Field removed.");
export const useReorderFields = () =>
  useCallFormsMutation(
    ({ templateVersionId, orders }) => api.reorderFields(templateVersionId, orders),
    "Order saved.",
  );

// Stage activities / primary form
export const useStageActivitiesForStage = (stageId) =>
  useQuery({
    queryKey: ["callforms", "stage-activities", stageId],
    queryFn: () => api.getStageActivitiesForStage(stageId),
    enabled: Boolean(stageId),
  });
export const useCreateStageActivity = () =>
  useCallFormsMutation(api.createStageActivity, "Form linked to stage.");
export const useUpdateStageActivity = () =>
  useCallFormsMutation(({ id, ...partial }) => api.updateStageActivity(id, partial), "Stage activity updated.");
export const useDeleteStageActivity = () =>
  useCallFormsMutation((id) => api.deleteStageActivity(id), "Stage activity removed.");
export const useSetPrimaryStageActivity = () =>
  useCallFormsMutation((id) => api.setPrimaryStageActivity(id), "Primary activity set.");
export const useLeadPrimaryForm = (leadId) =>
  useQuery({
    queryKey: ["callforms", "lead-primary-form", leadId],
    queryFn: () => api.getLeadPrimaryForm(leadId),
    enabled: Boolean(leadId),
    staleTime: 30 * 1000,
  });
export const useLeadStageForms = (leadId, stageId) =>
  useQuery({
    queryKey: ["callforms", "lead-stage-forms", leadId, stageId],
    queryFn: () => api.getLeadStageForms(leadId, stageId),
    enabled: Boolean(leadId || stageId),
    staleTime: 30 * 1000,
  });

// Attempts / submissions
export const useLogAttempt = () =>
  useCallFormsMutation(api.logCallAttempt);
export const useSubmitForm = () =>
  useCallFormsMutation(api.submitForm, "Form submitted.");
export const useLeadTimeline = (params) =>
  useQuery({
    queryKey: ["callforms", "timeline", params],
    queryFn: () => api.getLeadTimeline(params ?? {}),
    enabled: Boolean(params?.lead_id),
  });
export const useAttemptHistory = (leadId) =>
  useQuery({
    queryKey: ["callforms", "attempt-history", leadId],
    queryFn: () => api.getAttemptHistory(leadId),
    enabled: Boolean(leadId),
  });

// Analytics
export const useSubmissionAnalytics = (templateVersionId) =>
  useQuery({
    queryKey: ["callforms", "analytics", templateVersionId],
    queryFn: () => api.getSubmissionAnalytics(templateVersionId),
    enabled: Boolean(templateVersionId),
  });

// Trigger rules
export const useTriggerRules = (versionId) =>
  useQuery({
    queryKey: ["callforms", "trigger-rules", versionId],
    queryFn: () => api.getTriggerRules(versionId ? { version: versionId } : {}),
  });
export const useCreateTriggerRule = () =>
  useCallFormsMutation(api.createTriggerRule, "Trigger rule created.");
export const useDeleteTriggerRule = () =>
  useCallFormsMutation((ruleId) => api.deleteTriggerRule(ruleId), "Rule deleted.");

// Adhoc proposals
export const useAdhocProposals = () =>
  useQuery({ queryKey: ["callforms", "adhoc-proposals"], queryFn: api.getAdhocProposals });
export const useCreateAdhocProposal = () =>
  useCallFormsMutation(api.createAdhocProposal, "Proposal submitted for review.");
export const useReviewAdhocProposal = () =>
  useCallFormsMutation(
    ({ proposalId, ...payload }) => api.reviewAdhocProposal(proposalId, payload),
    "Review recorded.",
  );

// Field mappings (ADMINISTRATION → Form Templates → Mapping)
export const useFieldMappings = (templateId) =>
  useQuery({ queryKey: ["callforms", "field-mappings", templateId], queryFn: () => api.getFieldMappings(templateId ? { template: templateId } : {}), enabled: Boolean(templateId) });
export const useCreateFieldMapping = () => useCallFormsMutation(api.createFieldMapping, "Mapping created.");
export const useUpdateFieldMapping = () => useCallFormsMutation(({ id, ...partial }) => api.updateFieldMapping(id, partial), "Mapping updated.");
export const useDeleteFieldMapping = () => useCallFormsMutation((id) => api.deleteFieldMapping(id), "Mapping removed.");
