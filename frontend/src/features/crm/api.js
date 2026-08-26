// Shared customer_management master data (lead sources, pipelines, stages).
// Endpoints verified in frontend/docs/API_CONTRACT.md.

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function getLeadSources() {
  const { data } = await apiClient.get(endpoints.crm.leadSources);
  return data;
}

export async function getPipelines() {
  const { data } = await apiClient.get(endpoints.crm.pipelines);
  return data;
}

export async function getPipelineStages(pipelineId) {
  const { data } = await apiClient.get(endpoints.crm.pipelineStages, {
    params: pipelineId ? { pipeline: pipelineId } : {},
  });
  return data;
}
