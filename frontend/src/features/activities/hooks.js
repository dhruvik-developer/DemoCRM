// Activity queries/mutations. Creating an activity with follow_up_required
// makes the backend auto-create a follow-up Task — surfaced via toast here,
// never recreated client-side (implementation plan Phase 8).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { crmKeys, customerKeys, leadKeys } from "@/api/queryKeys";
import { getApiErrorMessage } from "@/utils/errors";
import { createActivity, getActivities } from "./api";

export function useActivities(filters) {
  return useQuery({
    queryKey: crmKeys.activities(filters),
    queryFn: () => getActivities(filters),
    // Endpoint returns a plain array (verified in views.py).
    select: (data) => (Array.isArray(data) ? data : (data?.results ?? [])),
  });
}

export function useCreateActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createActivity,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: crmKeys.activities });
      if (variables.lead) {
        queryClient.invalidateQueries({ queryKey: leadKeys.detail(variables.lead) });
      }
      if (variables.customer) {
        queryClient.invalidateQueries({
          queryKey: customerKeys.detail(variables.customer),
        });
      }
      toast.success(
        variables.follow_up_required
          ? "Activity logged. A follow-up task was created automatically."
          : "Activity logged.",
      );
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}
