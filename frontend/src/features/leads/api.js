// Leads API — every path verified in frontend/docs/API_CONTRACT.md.
// Workflow rules enforced server-side (see AUTH_CONTRACT/PERMISSION_CONTRACT):
// create must target the pipeline's FIRST stage; status is never directly
// editable; lost requires a reason; reengage only from LOST.

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function getLeads(filters) {
  const { data } = await apiClient.get(endpoints.crm.leads, { params: filters });
  return data;
}

export async function getLead(leadId) {
  const { data } = await apiClient.get(endpoints.crm.leadDetail(leadId));
  return data;
}

export async function createLead(values) {
  const { data } = await apiClient.post(endpoints.crm.leads, values);
  return data;
}

export async function assignLead(leadId, assignedTo) {
  const { data } = await apiClient.post(endpoints.crm.leadAssign(leadId), {
    assigned_to: assignedTo,
  });
  return data;
}

export async function progressLead(leadId, stageId) {
  const { data } = await apiClient.post(endpoints.crm.leadProgress(leadId), stageId ? { stage_id: stageId } : {});
  return data;
}

export async function markLeadLost(leadId, lostReason) {
  const { data } = await apiClient.post(endpoints.crm.leadLost(leadId), {
    lost_reason: lostReason,
  });
  return data;
}

export async function reengageLead(leadId) {
  const { data } = await apiClient.post(endpoints.crm.leadReengage(leadId));
  return data;
}

/**
 * Idempotent per backend rules: exact email+phone match returns the existing
 * customer (201); email-or-phone-alone collision returns 400 duplicate.
 */
export async function convertLead(leadId, payload) {
  const { data } = await apiClient.post(endpoints.crm.leadConvert(leadId), payload);
  return data;
}
