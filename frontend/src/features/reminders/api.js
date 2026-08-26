// Reminders API — POST + detail + status only; no list endpoint exists (G8).
// Celery jobs handle due-reminder delivery; the UI only manages records.

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function createReminder(values) {
  const { data } = await apiClient.post(endpoints.reminders.create, values);
  return data;
}

export async function getReminder(reminderId) {
  const { data } = await apiClient.get(endpoints.reminders.detail(reminderId));
  return data;
}

export async function updateReminderStatus(reminderId, statusId) {
  const { data } = await apiClient.patch(endpoints.reminders.status(reminderId), {
    reminder_status_id: statusId,
  });
  return data;
}
