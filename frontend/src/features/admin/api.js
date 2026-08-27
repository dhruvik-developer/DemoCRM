// Admin API — roles, permissions, role assignment.
// Verified in frontend/docs/API_CONTRACT.md + PERMISSION_CONTRACT.md.

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

const unwrap = (data) => (Array.isArray(data) ? data : (data?.results ?? []));

/** { message, roles: [{role_id, rolename, description, permissions}] } */
export async function getRoles() {
  const { data } = await apiClient.get(endpoints.auth.roles);
  return data.roles ?? [];
}

export async function createRole(values) {
  const { data } = await apiClient.post(endpoints.auth.roles, values);
  return data;
}

/** PATCH merges the given permission ids into the role. */
export async function updateRole(roleId, partial) {
  const { data } = await apiClient.patch(endpoints.auth.roleDetail(roleId), partial);
  return data;
}

export async function deleteRole(roleId) {
  const { data } = await apiClient.delete(endpoints.auth.roleDetail(roleId));
  return data;
}

export async function getPermissions() {
  const { data } = await apiClient.get(endpoints.auth.permissions);
  return unwrap(data);
}

export async function getUsers() {
  const { data } = await apiClient.get(endpoints.auth.users);
  return data?.users ?? data?.results ?? (Array.isArray(data) ? data : []);
}

/** PUT /assign-role/<uuid>/ — {role_id} required. */
export async function assignRole(userId, roleId) {
  const { data } = await apiClient.put(endpoints.auth.assignRole(userId), {
    role_id: roleId,
  });
  return data;
}
