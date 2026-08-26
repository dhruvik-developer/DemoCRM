// Meetings API — endpoints verified in frontend/docs/API_CONTRACT.md.
// No list endpoint exists (G8): create returns the meeting, then we navigate
// to its detail. Approval is owner-manager-only; reschedule creator-only and
// only from REJECTED.

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function createMeeting(values) {
  const { data } = await apiClient.post(endpoints.meetings.create, values);
  return data;
}

export async function getMeeting(meetingId) {
  const { data } = await apiClient.get(endpoints.meetings.detail(meetingId));
  return data;
}

export async function decideMeetingApproval(meetingId, payload) {
  const { data } = await apiClient.patch(
    endpoints.meetings.approval(meetingId),
    payload,
  );
  return data;
}

export async function rescheduleMeeting(meetingId, payload) {
  const { data } = await apiClient.patch(
    endpoints.meetings.reschedule(meetingId),
    payload,
  );
  return data;
}

export async function updateMeetingStatus(meetingId, meetingStatusId) {
  const { data } = await apiClient.patch(endpoints.meetings.status(meetingId), {
    meeting_status_id: meetingStatusId,
  });
  return data;
}

export async function addMeetingParticipant(meetingId, values) {
  const { data } = await apiClient.post(
    endpoints.meetings.participants(meetingId),
    values,
  );
  return data;
}

export async function removeMeetingParticipant(meetingId, userId) {
  const { data } = await apiClient.delete(
    endpoints.meetings.participantDetail(meetingId, userId),
  );
  return data;
}
