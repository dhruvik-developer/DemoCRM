// Notifications API — verified in frontend/docs/API_CONTRACT.md.
// Inbox is owner-scoped server-side; mark-read is idempotent.
// NOTE: there is no bulk mark-all-read endpoint — the client loops.

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function getNotifications(filters) {
  const { data } = await apiClient.get(endpoints.notifications.list, {
    params: filters,
  });
  return data;
}

export async function getNotificationTemplates(filters) {
  const { data } = await apiClient.get(endpoints.notifications.templates, {
    params: filters,
  });
  return data;
}

export async function createNotificationTemplate(values) {
  const { data } = await apiClient.post(endpoints.notifications.templates, values);
  return data;
}

/** Soft delete on the backend (is_active=False). */
export async function deleteNotificationTemplate(templateId) {
  const { data } = await apiClient.delete(
    endpoints.notifications.templateDetail(templateId),
  );
  return data;
}

/**
 * Exactly one of recipient_id / recipient_ids is required server-side.
 * event_type defaults to MANUAL when omitted.
 */
export async function sendManualNotification(values) {
  const { data } = await apiClient.post(endpoints.notifications.send, values);
  return data;
}

export async function markNotificationRead(notificationId) {
  const { data } = await apiClient.patch(
    endpoints.notifications.markRead(notificationId),
    {},
  );
  return data;
}
