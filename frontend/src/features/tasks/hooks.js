// Task queries + mutations. Mutations invalidate taskKeys; the activity feed
// and lead detail also reflect task events server-side.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { taskKeys } from "@/api/queryKeys";
import { getApiErrorMessage } from "@/utils/errors";
import {
  assignTask,
  createTask,
  deleteTask,
  getTask,
  getTasks,
  getTaskKpi,
  getTaskStatuses,
  getTaskCategories,
  updateTask,
  updateTaskStatus,
} from "./api";

export function useTasks(filters) {
  return useQuery({
    queryKey: taskKeys.list(filters),
    queryFn: () => getTasks(filters),
    placeholderData: (previous) => previous,
  });
}

export function useTaskKpi() {
  return useQuery({
    queryKey: ["tasks", "kpi"],
    queryFn: getTaskKpi,
  });
}

export function useTask(taskId) {
  return useQuery({
    queryKey: taskKeys.detail(taskId),
    queryFn: () => getTask(taskId),
    enabled: Boolean(taskId),
  });
}

function useInvalidateTasks() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: taskKeys.all });
}

export function useCreateTask() {
  const invalidate = useInvalidateTasks();
  return useMutation({
    mutationFn: createTask,
    onSuccess: (task) => {
      invalidate();
      toast.success("Task created.");
      return task;
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useUpdateTask(taskId) {
  const invalidate = useInvalidateTasks();
  return useMutation({
    mutationFn: (values) => updateTask(taskId, values),
    onSuccess: () => {
      invalidate();
      toast.success("Task updated.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useAssignTask(taskId) {
  const invalidate = useInvalidateTasks();
  return useMutation({
    mutationFn: (assignedTo) => assignTask(taskId, assignedTo),
    onSuccess: () => {
      invalidate();
      toast.success("Task reassigned.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useUpdateTaskStatus(taskId) {
  const invalidate = useInvalidateTasks();
  return useMutation({
    mutationFn: (statusId) => updateTaskStatus(taskId, statusId),
    onSuccess: () => {
      invalidate();
      toast.success("Task status updated.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useDeleteTask(taskId) {
  const invalidate = useInvalidateTasks();
  return useMutation({
    mutationFn: (id) => deleteTask(taskId ?? id),
    onSuccess: () => {
      invalidate();
      toast.success("Task deleted.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useTaskStatuses() {
  return useQuery({
    queryKey: ["tasks", "master-statuses"],
    queryFn: getTaskStatuses,
    staleTime: 5 * 60 * 1000, // 5 minutes cache
  });
}


export function useTaskCategories() {
  return useQuery({
    queryKey: ["tasks", "master-categories"],
    queryFn: getTaskCategories,
    staleTime: 5 * 60 * 1000,
  });
}

