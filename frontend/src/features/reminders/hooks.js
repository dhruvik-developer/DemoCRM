// Reminder mutations. No list query exists by design (G8).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { reminderKeys } from "@/api/queryKeys";
import { getApiErrorMessage } from "@/utils/errors";
import { createReminder, getReminder, updateReminderStatus } from "./api";

export function useReminder(reminderId) {
  return useQuery({
    queryKey: reminderKeys.detail(reminderId),
    queryFn: () => getReminder(reminderId),
    enabled: Boolean(reminderId),
  });
}

function useInvalidateReminders() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: reminderKeys.all });
}

export function useCreateReminder() {
  const invalidate = useInvalidateReminders();
  return useMutation({
    mutationFn: createReminder,
    onSuccess: () => {
      invalidate();
      toast.success("Reminder created.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useUpdateReminderStatus(reminderId) {
  const invalidate = useInvalidateReminders();
  return useMutation({
    mutationFn: (statusId) => updateReminderStatus(reminderId, statusId),
    onSuccess: () => {
      invalidate();
      toast.success("Reminder status updated.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}
