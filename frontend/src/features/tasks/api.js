// Tasks API — endpoints verified in frontend/docs/API_CONTRACT.md.
// Visibility is server-side: Admin/Manager see all active tasks, Employees
// only their own. DELETE is a soft delete (is_active=False).

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function getTasks(filters) {
  const { data } = await apiClient.get(endpoints.tasks.list, { params: filters });
  return data;
}

export async function getTask(taskId) {
  const { data } = await apiClient.get(endpoints.tasks.detail(taskId));
  return data;
}

export async function createTask(values) {
  const { data } = await apiClient.post(endpoints.tasks.list, values);
  return data;
}

export async function updateTask(taskId, partial) {
  const { data } = await apiClient.patch(endpoints.tasks.detail(taskId), partial);
  return data;
}

/** Soft delete — backend sets is_active=False. */
export async function deleteTask(taskId) {
  const { data } = await apiClient.delete(endpoints.tasks.detail(taskId));
  return data;
}

export async function assignTask(taskId, assignedTo) {
  const { data } = await apiClient.post(endpoints.tasks.assign(taskId), {
    assigned_to: assignedTo,
  });
  return data;
}

export async function updateTaskStatus(taskId, statusId) {
  const { data } = await apiClient.patch(endpoints.tasks.status(taskId), {
    status_id: statusId,
  });
  return data;
}

export async function getTaskStatuses() {
  const { data } = await apiClient.get(endpoints.tasks.masterStatuses);
  return data?.task_statuses || [];
}

export async function getTaskCategories() {
  const { data } = await apiClient.get(endpoints.tasks.masterCategories);
  return data?.task_categories || [];
}