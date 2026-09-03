import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function getRecordNotes(entityType, entityId) {
  const { data } = await apiClient.get(endpoints.notes.list, { params: { entity_type: entityType, entity_id: entityId } });
  return data;
}

export async function createRecordNote(values) {
  const { data } = await apiClient.post(endpoints.notes.list, values);
  return data;
}
