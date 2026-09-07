// Queries for shared CRM master data used by Leads/Customers forms.
// Results may be plain arrays or paginated envelopes depending on the view —
// normalize both here so consumers always get an array.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { crmKeys } from "@/api/queryKeys";
import { getApiErrorMessage } from "@/utils/errors";
import {
  createLeadSource,
  createPipeline,
  createPipelineStage,
  deleteLeadSource,
  deletePipeline,
  deletePipelineStage,
  getLeadSources,
  getPipelines,
  getPipelineStages,
  updateLeadSource,
  updatePipeline,
} from "./api";

function toArray(data) {
  if (Array.isArray(data)) return data;
  return data?.results ?? [];
}

export function useLeadSources() {
  return useQuery({
    queryKey: crmKeys.leadSources,
    queryFn: async () => toArray(await getLeadSources()),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

function useInvalidateCRM() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: crmKeys.leadSources });
}

export function useCreateLeadSource() {
  const invalidate = useInvalidateCRM();
  return useMutation({
    mutationFn: createLeadSource,
    onSuccess: () => {
      invalidate();
      toast.success("Lead source created.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useUpdateLeadSource() {
  const invalidate = useInvalidateCRM();
  return useMutation({
    mutationFn: ({ id, ...partial }) => updateLeadSource(id, partial),
    onSuccess: () => {
      invalidate();
      toast.success("Lead source updated.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useDeleteLeadSource() {
  const invalidate = useInvalidateCRM();
  return useMutation({
    mutationFn: (id) => deleteLeadSource(id),
    onSuccess: () => {
      invalidate();
      toast.success("Lead source deleted.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function usePipelines() {
  return useQuery({
    queryKey: crmKeys.pipelines,
    queryFn: async () => toArray(await getPipelines()),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useCreatePipeline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createPipeline,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: crmKeys.pipelines });
      // Fresh pipeline clones stage skeleton server-side (forms NOT copied → isolated control).
      queryClient.invalidateQueries({ queryKey: ["crm", "pipeline-stages"] });
      toast.success("Pipeline created. Stages copied (forms are empty — link forms per pipeline).");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useUpdatePipeline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...partial }) => updatePipeline(id, partial),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: crmKeys.pipelines });
      toast.success("Pipeline updated.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useDeletePipeline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => deletePipeline(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: crmKeys.pipelines });
      queryClient.invalidateQueries({ queryKey: ["crm", "pipeline-stages"] });
      queryClient.invalidateQueries({ queryKey: ["callforms"] });
      toast.success("Pipeline deleted (only its stages & forms removed).");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useCreatePipelineStage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createPipelineStage,
    onSuccess: (result) => {
      // Isolated: invalidate both generic and pipeline-specific keys, and also all pipeline views
      queryClient.invalidateQueries({ queryKey: ["crm", "pipeline-stages"] });
      if (result?.pipeline) queryClient.invalidateQueries({ queryKey: crmKeys.pipelineStages(result.pipeline) });
      toast.success("Pipeline stage created.");
      return result;
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useDeletePipelineStage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => deletePipelineStage(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm", "pipeline-stages"] });
      toast.success("Pipeline stage deleted.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

/** Stages are ordered by display_order server-side; first stage = index 0. */
export function usePipelineStages(pipelineId) {
  return useQuery({
    queryKey: crmKeys.pipelineStages(pipelineId),
    queryFn: async () => toArray(await getPipelineStages(pipelineId)),
    enabled: Boolean(pipelineId),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

/**
 * Serializers expose raw FK ids only (no *_details), so list/detail views
 * resolve names client-side from this cached map.
 * @returns {{ isLoading: boolean, sourceName: (id) => string|null, pipelineName: (id) => string|null, stageName: (id) => string|null }}
 */
export function useMasterDataMaps() {
  const sourcesQuery = useLeadSources();
  const pipelinesQuery = usePipelines();
  const allStagesQuery = useQuery({
    queryKey: [...crmKeys.pipelineStages(null), "all"],
    queryFn: async () => toArray(await getPipelineStages(null)),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const isLoading =
    sourcesQuery.isLoading || pipelinesQuery.isLoading || allStagesQuery.isLoading;

  const index = (rows, key) =>
    Object.fromEntries((rows ?? []).map((row) => [row.id ?? row[key], row]));

  const sources = index(sourcesQuery.data);
  const stages = index(allStagesQuery.data);

  return {
    isLoading,
    sourceName: (id) => sources[id]?.name ?? null,
    pipelineName: (id) =>
      (pipelinesQuery.data ?? []).find((pipeline) => pipeline.id === id)?.name ?? null,
    stageName: (id) => stages[id]?.name ?? null,
  };
}
