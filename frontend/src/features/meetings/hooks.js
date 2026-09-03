// Meeting queries/mutations. The detail query key also feeds the approval /
// reschedule / participant mutations' invalidation.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { meetingKeys } from "@/api/queryKeys";
import { getApiErrorMessage } from "@/utils/errors";
import {
  addMeetingParticipant,
  createMeeting,
  decideMeetingApproval,
  getMeeting,
  getMeetings,
  getMeetingKpi,
  removeMeetingParticipant,
  rescheduleMeeting,
  updateMeetingStatus,
} from "./api";

export function useMeetings(filters) {
  return useQuery({
    queryKey: meetingKeys.list(filters),
    queryFn: () => getMeetings(filters),
    placeholderData: (previous) => previous,
  });
}

export function useMeetingKpi() {
  return useQuery({
    queryKey: ["meetings", "kpi"],
    queryFn: getMeetingKpi,
  });
}

export function useMeeting(meetingId) {
  return useQuery({
    queryKey: meetingKeys.detail(meetingId),
    queryFn: () => getMeeting(meetingId),
    enabled: Boolean(meetingId),
  });
}

function useInvalidateMeeting() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: meetingKeys.all });
}

export function useCreateMeeting() {
  const invalidate = useInvalidateMeeting();
  return useMutation({
    mutationFn: createMeeting,
    onSuccess: (meeting) => {
      invalidate();
      toast.success("Meeting requested — waiting for manager approval.");
      return meeting;
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useDecideApproval(meetingId) {
  const invalidate = useInvalidateMeeting(meetingId);
  return useMutation({
    mutationFn: (payload) => {
      const id = payload.meetingId || meetingId;
      const { meetingId: _, ...rest } = payload;
      return decideMeetingApproval(id, rest);
    },
    onSuccess: (_data, payload) => {
      invalidate();
      toast.success(
        payload.approval_status === "APPROVED" || payload.decision === "APPROVE"
          ? "Meeting approved — invites and link are being sent."
          : "Meeting rejected.",
      );
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useRescheduleMeeting(meetingId) {
  const invalidate = useInvalidateMeeting(meetingId);
  return useMutation({
    mutationFn: (payload) => {
      const id = payload.meetingId || meetingId;
      const { meetingId: _, ...rest } = payload;
      return rescheduleMeeting(id, rest);
    },
    onSuccess: () => {
      invalidate();
      toast.success("Meeting rescheduled — sent back to manager for approval.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useUpdateMeetingStatus(meetingId) {
  const invalidate = useInvalidateMeeting(meetingId);
  return useMutation({
    mutationFn: (meetingStatusId) => updateMeetingStatus(meetingId, meetingStatusId),
    onSuccess: () => {
      invalidate();
      toast.success("Meeting status updated.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useAddParticipant(meetingId) {
  const invalidate = useInvalidateMeeting(meetingId);
  return useMutation({
    mutationFn: (values) => addMeetingParticipant(meetingId, values),
    onSuccess: () => {
      invalidate();
      toast.success("Participant added.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useRemoveParticipant(meetingId) {
  const invalidate = useInvalidateMeeting(meetingId);
  return useMutation({
    mutationFn: (userId) => removeMeetingParticipant(meetingId, userId),
    onSuccess: () => {
      invalidate();
      toast.success("Participant removed.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}
