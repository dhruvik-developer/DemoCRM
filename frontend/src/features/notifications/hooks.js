// Notification queries/mutations. The unread count query mirrors the bell's
// 30s polling; mark-read invalidates both inbox and bell count.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { notificationKeys } from "@/api/queryKeys";
import { getApiErrorMessage } from "@/utils/errors";
import {
  createNotificationTemplate,
  deleteNotificationTemplate,
  getNotificationTemplates,
  getNotifications,
  markNotificationRead,
  sendManualNotification,
} from "./api";

export function useNotifications(filters) {
  return useQuery({
    queryKey: notificationKeys.inbox(filters),
    queryFn: () => getNotifications(filters),
    refetchInterval: 30000, // matches the bell + backend job cadence
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: ["notifications", "inbox", { is_read: "false", page_size: 1 }],
    queryFn: () =>
      getNotifications({ is_read: "false", page_size: 1 }).then(
        (data) => data?.count ?? 0,
      ),
    refetchInterval: 30000,
  });
}

export function useMarkAllRead(unreadIds) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      // No bulk endpoint — sequential idempotent calls (G-gap noted in code).
      for (const id of unreadIds ?? []) {
        await markNotificationRead(id);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
      toast.success("All notifications marked as read.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId) => markNotificationRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useNotificationTemplates(filters) {
  return useQuery({
    queryKey: notificationKeys.templates(filters),
    queryFn: () => getNotificationTemplates(filters),
    placeholderData: (previous) => previous,
  });
}

function useInvalidateTemplates() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: notificationKeys.templates });
}

export function useCreateNotificationTemplate() {
  const invalidate = useInvalidateTemplates();
  return useMutation({
    mutationFn: createNotificationTemplate,
    onSuccess: () => {
      invalidate();
      toast.success("Template created.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useDeleteNotificationTemplate() {
  const invalidate = useInvalidateTemplates();
  return useMutation({
    mutationFn: (templateId) => deleteNotificationTemplate(templateId),
    onSuccess: () => {
      invalidate();
      toast.success("Template deactivated.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useSendManualNotification() {
  return useMutation({
    mutationFn: sendManualNotification,
    onSuccess: () => toast.success("Notification sent."),
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}
