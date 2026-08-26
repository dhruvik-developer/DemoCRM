// Queries for shared CRM master data used by Leads/Customers forms.
// Results may be plain arrays or paginated envelopes depending on the view —
// normalize both here so consumers always get an array.

import { useQuery } from "@tanstack/react-query";
import { crmKeys } from "@/api/queryKeys";
import { getLeadSources, getPipelines, getPipelineStages } from "./api";

function toArray(data) {
  if (Array.isArray(data)) return data;
  return data?.results ?? [];
}

export function useLeadSources() {
  return useQuery({
    queryKey: crmKeys.leadSources,
    queryFn: async () => toArray(await getLeadSources()),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePipelines() {
  return useQuery({
    queryKey: crmKeys.pipelines,
    queryFn: async () => toArray(await getPipelines()),
    staleTime: 5 * 60 * 1000,
  });
}

/** Stages are ordered by display_order server-side; first stage = index 0. */
export function usePipelineStages(pipelineId) {
  return useQuery({
    queryKey: crmKeys.pipelineStages(pipelineId),
    queryFn: async () => toArray(await getPipelineStages(pipelineId)),
    enabled: Boolean(pipelineId),
    staleTime: 5 * 60 * 1000,
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
