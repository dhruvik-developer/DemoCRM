// Follow-up queries + mutations. Create gates on change_followup (G13) in
// the UI just as the backend does; delete warns because it's a HARD delete.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { followUpKeys } from "@/api/queryKeys";
import { getApiErrorMessage } from "@/utils/errors";
import {
  createFollowUp,
  deleteFollowUp,
  getFollowUps,
  updateFollowUpStatus,
} from "./api";

export function useFollowUps(filters) {
  return useQuery({
    queryKey: followUpKeys.list(filters),
    queryFn: () => getFollowUps(filters),
    placeholderData: (previous) => previous,
  });
}

function useInvalidateFollowUps() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: followUpKeys.all });
}

export function useCreateFollowUp() {
  const invalidate = useInvalidateFollowUps();
  return useMutation({
    mutationFn: createFollowUp,
    onSuccess: () => {
      invalidate();
      toast.success("Follow-up scheduled.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useDeleteFollowUp() {
  const invalidate = useInvalidateFollowUps();
  return useMutation({
    mutationFn: (followUpId) => deleteFollowUp(followUpId),
    onSuccess: () => {
      invalidate();
      toast.success("Follow-up deleted permanently.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useUpdateFollowUpStatus() {
  const invalidate = useInvalidateFollowUps();
  return useMutation({
    mutationFn: ({ followUpId, statusId }) =>
      updateFollowUpStatus(followUpId, statusId),
    onSuccess: () => {
      invalidate();
      toast.success("Follow-up status updated.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}
