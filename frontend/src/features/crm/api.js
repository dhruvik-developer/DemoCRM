// Shared customer_management master data (lead sources, pipelines, stages).
// Endpoints verified in frontend/docs/API_CONTRACT.md.

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function getLeadSources() {
  const { data } = await apiClient.get(endpoints.crm.leadSources);
  return data;
}

export async function createLeadSource(values) {
  const { data } = await apiClient.post(endpoints.crm.leadSources, values);
  return data;
}

export async function updateLeadSource(id, partial) {
  const { data } = await apiClient.patch(endpoints.crm.leadSourceDetail(id), partial);
  return data;
}

export async function deleteLeadSource(id) {
  const { data } = await apiClient.delete(endpoints.crm.leadSourceDetail(id));
  return data;
}

export async function getPipelines() {
  const { data } = await apiClient.get(endpoints.crm.pipelines);
  return data;
}

export async function createPipeline(values) {
  const { data } = await apiClient.post(endpoints.crm.pipelines, values);
  return data;
}

export async function updatePipeline(id, partial) {
  const { data } = await apiClient.patch(endpoints.crm.pipelineDetail(id), partial);
  return data;
}

export async function deletePipeline(id) {
  const { data } = await apiClient.delete(endpoints.crm.pipelineDetail(id));
  return data;
}

export async function getPipelineStages(pipelineId) {
  const { data } = await apiClient.get(endpoints.crm.pipelineStages, {
    params: pipelineId ? { pipeline: pipelineId } : {},
  });
  return data;
}

export async function createPipelineStage(values) {
  const { data } = await apiClient.post(endpoints.crm.pipelineStages, values);
  return data;
}

export async function deletePipelineStage(id) {
  const { data } = await apiClient.delete(endpoints.crm.pipelineStageDetail(id));
  return data;
}
