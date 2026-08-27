// Lead queries + mutations. Mutations invalidate leadKeys/customerKeys and
// toast outcomes; field errors are attached to the error for form consumers.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { customerKeys, leadKeys } from "@/api/queryKeys";
import { getApiErrorMessage } from "@/utils/errors";
import {
  assignLead,
  convertLead,
  createLead,
  getLead,
  getLeads,
  markLeadLost,
  progressLead,
  reengageLead,
} from "./api";

export function useLeads(filters) {
  return useQuery({
    queryKey: leadKeys.list(filters),
    queryFn: async () => {
      const data = await getLeads(filters);
      if (Array.isArray(data)) {
        return { count: data.length, results: data };
      }
      return data;
    },
    placeholderData: (previous) => previous, // keep table stable across page/filter changes
  });
}

export function useLead(leadId) {
  return useQuery({
    queryKey: leadKeys.detail(leadId),
    queryFn: () => getLead(leadId),
    enabled: Boolean(leadId),
  });
}

function useInvalidateLeads() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: leadKeys.all });
    // Conversion creates a Customer — keep that module fresh too.
    queryClient.invalidateQueries({ queryKey: customerKeys.all });
  };
}

export function useCreateLead() {
  const invalidate = useInvalidateLeads();
  return useMutation({
    mutationFn: createLead,
    onSuccess: () => {
      invalidate();
      toast.success("Lead created.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useAssignLead(leadId) {
  const invalidate = useInvalidateLeads();
  return useMutation({
    mutationFn: (assignedTo) => assignLead(leadId, assignedTo),
    onSuccess: () => {
      invalidate();
      toast.success("Lead reassigned.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useProgressLead(leadId) {
  const invalidate = useInvalidateLeads();
  return useMutation({
    mutationFn: (stageId) => progressLead(leadId, stageId),
    onSuccess: () => {
      invalidate();
      toast.success("Lead moved to the next stage.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useMarkLeadLost(leadId) {
  const invalidate = useInvalidateLeads();
  return useMutation({
    mutationFn: (lostReason) => markLeadLost(leadId, lostReason),
    onSuccess: () => {
      invalidate();
      toast.success("Lead marked as lost.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useReengageLead(leadId) {
  const invalidate = useInvalidateLeads();
  return useMutation({
    mutationFn: () => reengageLead(leadId),
    onSuccess: () => {
      invalidate();
      toast.success("Lead re-engaged.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useConvertLead(leadId) {
  const invalidate = useInvalidateLeads();
  return useMutation({
    mutationFn: (payload) => convertLead(leadId, payload),
    onSuccess: () => {
      invalidate();
      toast.success("Lead converted to a customer.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}
