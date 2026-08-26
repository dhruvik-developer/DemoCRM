// Auth API calls. Response shapes are documented in
// frontend/docs/AUTH_CONTRACT.md — keep this file in sync with it.

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function loginRequest(values) {
  const { data } = await apiClient.post(endpoints.auth.login, values);
  return data; // { message, access_token, refresh_token }
}

export async function registerRequest(values) {
  const { data } = await apiClient.post(endpoints.auth.register, values);
  return data; // { user_id, username, email, message }
}

export async function logoutRequest(refreshToken) {
  const { data } = await apiClient.post(endpoints.auth.logout, {
    refresh_token: refreshToken,
  });
  return data;
}

export async function fetchProfile(userId) {
  const { data } = await apiClient.get(endpoints.auth.profile(userId));
  return data.profile; // nested — verified via live schema
}

export async function forgotPasswordRequest(values) {
  const { data } = await apiClient.post(endpoints.auth.forgotPassword, values);
  return data;
}

export async function resetPasswordRequest(values) {
  const { data } = await apiClient.post(endpoints.auth.resetPassword, values);
  return data;
}

export async function changePasswordRequest(values) {
  const { data } = await apiClient.post(endpoints.auth.changePassword, values);
  return data;
}
