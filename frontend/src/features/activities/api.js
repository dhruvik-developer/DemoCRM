// Activities API — list+create only (backend exposes no update/delete routes
// for activities). GET returns a plain array (not paginated); business-rule
// failures return {"detail": "..."} with 400 (XOR lead/customer, CONVERTED
// lead block, follow-up cross-check).

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function getActivities(filters) {
  const { data } = await apiClient.get(endpoints.crm.activities, {
    params: filters,
  });
  return data;
}

export async function createActivity(values) {
  const { data } = await apiClient.post(endpoints.crm.activities, values);
  return data;
}
