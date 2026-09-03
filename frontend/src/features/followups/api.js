// FollowUps API — verified in frontend/docs/API_CONTRACT.md.
// Gotchas: the description field is literally named `decription` (G12); POST
// is gated on change_followup, NOT add_followup (G13); DELETE is a HARD delete.

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function getFollowUps(filters) {
  const { data } = await apiClient.get(endpoints.followups.list, {
    params: filters,
  });
  return data;
}

export async function getFollowUpKpi() {
  const { data } = await apiClient.get(endpoints.followups.kpi);
  return data;
}

export async function getFollowUp(followUpId) {
  const { data } = await apiClient.get(endpoints.followups.detail(followUpId));
  return data;
}

export async function createFollowUp(values) {
  const { data } = await apiClient.post(endpoints.followups.list, values);
  return data;
}

export async function updateFollowUp(followUpId, partial) {
  const { data } = await apiClient.patch(endpoints.followups.detail(followUpId), partial);
  return data;
}

export async function deleteFollowUp(followUpId) {
  const { data } = await apiClient.delete(endpoints.followups.detail(followUpId));
  return data;
}

export async function updateFollowUpStatus(followUpId, statusId) {
  const { data } = await apiClient.patch(endpoints.followups.status(followUpId), {
    status_id: statusId,
  });
  return data;
}
