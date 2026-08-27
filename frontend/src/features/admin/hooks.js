// Admin queries/mutations. Only Admins (and Managers for reads) can call
// these — the sidebar hides the entry for everyone else via view_role.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { authKeys } from "@/api/queryKeys";
import { getApiErrorMessage } from "@/utils/errors";
import {
  assignRole,
  createRole,
  deleteRole,
  getPermissions,
  getRoles,
  getUsers,
  updateRole,
} from "./api";

export function useRoles() {
  return useQuery({ queryKey: ["admin", "roles"], queryFn: getRoles });
}

export function usePermissions() {
  return useQuery({
    queryKey: ["admin", "permissions"],
    queryFn: getPermissions,
    staleTime: 5 * 60 * 1000,
  });
}

export function useUsers() {
  return useQuery({
    queryKey: ["admin", "users"],
    queryFn: getUsers,
    staleTime: 60 * 1000,
  });
}

function useInvalidateAdmin() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["admin"] });
}

export function useCreateRole() {
  const invalidate = useInvalidateAdmin();
  return useMutation({
    mutationFn: createRole,
    onSuccess: () => {
      invalidate();
      toast.success("Role created.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useUpdateRole() {
  const invalidate = useInvalidateAdmin();
  return useMutation({
    mutationFn: ({ roleId, ...partial }) => updateRole(roleId, partial),
    onSuccess: () => {
      invalidate();
      toast.success("Role updated.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useDeleteRole() {
  const invalidate = useInvalidateAdmin();
  return useMutation({
    mutationFn: (roleId) => deleteRole(roleId),
    onSuccess: () => {
      invalidate();
      toast.success("Role deleted.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useAssignRole() {
  const invalidate = useInvalidateAdmin();
  return useMutation({
    mutationFn: ({ userId, roleId }) => assignRole(userId, roleId),
    onSuccess: () => {
      invalidate();
      toast.success("Role assigned.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export { authKeys };
