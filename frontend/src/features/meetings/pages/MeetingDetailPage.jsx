// Meeting detail: info card + manager approval panel + reschedule + status +
// participants. Button visibility follows backend rules:
// - Approve/Reject: only meeting.manager == current user, role Manager, PENDING
// - Reschedule: only creator, only when REJECTED
// Note: the API exposes no participant roster (MeetingSerializer is scalar) —
// add/remove operate by user UUID (filed under G8's serializer gap).

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { meetingStatusName, meetingTypeName } from "@/utils/meetingMasterData";
import {
  useAddParticipant,
  useDecideApproval,
  useMeeting,
  useRemoveParticipant,
  useRescheduleMeeting,
} from "../hooks";
import { useUsers } from "@/features/admin/hooks";
import { approvalDecisionSchema } from "@/schemas/meeting.schema";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import StatusBadge from "@/components/common/StatusBadge";
import FormField from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function Field({ label, value }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="text-sm">{value ?? "—"}</span>
    </div>
  );
}

export default function MeetingDetailPage() {
  const { meetingId } = useParams();
  const { user, resolved } = useAuth();
  const meetingQuery = useMeeting(meetingId);
  const { data: users = [] } = useUsers();

  const decideApproval = useDecideApproval(meetingId);
  const reschedule = useRescheduleMeeting(meetingId);
  const addParticipant = useAddParticipant(meetingId);
  const removeParticipant = useRemoveParticipant(meetingId);

  const [rejectOpen, setRejectOpen] = useState(false);
  const [participantId, setParticipantId] = useState("");
  const [removeId, setRemoveId] = useState("");

  const rejectionForm = useForm({
    resolver: zodResolver(approvalDecisionSchema),
    defaultValues: { rejection_reason: "" },
  });

  if (meetingQuery.isLoading) return <PageLoader label="Loading meeting…" />;
  if (meetingQuery.isError) {
    return <PageError error={meetingQuery.error} onRetry={meetingQuery.refetch} />;
  }

  const meeting = meetingQuery.data;
  const can = (codename) => hasPermission(resolved, codename);

  const isAssignedManager =
    user?.user_id != null &&
    String(meeting?.manager?.user_id ?? meeting?.manager ?? "") === String(user.user_id);
  const isCreator =
    user?.user_id != null &&
    String(meeting?.created_by?.user_id ?? meeting?.created_by ?? "") === String(user.user_id);
  const isManagerRole =
    resolved?.isAdmin ||
    resolved?.roleName === "Manager" ||
    String(resolved?.roleName || "").toLowerCase() === "manager";

  const isEmployeeRole = resolved?.roleName === "Employee";

  const isPending = meeting?.approval_status === "PENDING";
  const isRejected = meeting?.approval_status === "REJECTED";

  const showApprovalActions = isPending && (isAssignedManager || isManagerRole);
  // Only Employee (creator) can reschedule — Manager cannot reschedule
  const showReschedule = isRejected && isCreator && isEmployeeRole;

  const onApprove = () =>
    decideApproval.mutateAsync({ approval_status: "APPROVED" });
  const onReject = rejectionForm.handleSubmit((values) =>
    decideApproval
      .mutateAsync({
        approval_status: "REJECTED",
        rejection_reason: values.rejection_reason || undefined,
      })
      .then(() => setRejectOpen(false)),
  );

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">
            {meeting.meeting_title}
          </h1>
          <StatusBadge status={meeting.approval_status} />
        </div>
        <Button variant="ghost" asChild>
          <Link to="/meetings">← Meetings</Link>
        </Button>
      </div>

      {isPending ? (
        <p className="rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-xs text-blue-900 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-200">
          Waiting for the assigned manager's decision. A reminder email goes out
          5 minutes before approved meetings.
        </p>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Meeting Information</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <Field label="Title" value={meeting.meeting_title} />
          <Field label="Related task" value={meeting.task_title} />
          <Field label="Approval" value={meeting.approval_status} />
          <Field label="Date" value={meeting.meeting_date} />
          <Field label="Start" value={meeting.start_time} />
          <Field label="End" value={meeting.end_time} />
          <Field label="Type" value={meetingTypeName(meeting.meeting_type_id?.id ?? meeting.meeting_type_id)} />
          <Field label="Status" value={meetingStatusName(meeting.meeting_status_id?.id ?? meeting.meeting_status_id)} />
          <Field label="Manager" value={meeting.manager_name} />
          <Field label="Requested by" value={meeting.requested_by_name} />
          <Field label="Created" value={meeting.created_at ? new Date(meeting.created_at).toLocaleString() : null} />
          <Field
            label="Manager"
            value={
              meeting.manager ? `${String(meeting.manager).slice(0, 8)}…` : null
            }
          />
          <div className="md:col-span-2">
            <Field label={meeting.meeting_link ? "Meeting link" : "Location"}
              value={meeting.meeting_link ?? meeting.location ?? null}
            />
          </div>
          {meeting.description ? <div className="md:col-span-3"><Field label="Description" value={meeting.description} /></div> : null}
          {meeting.rejection_reason ? (
            <div className="md:col-span-3">
              <Field label="Rejection reason" value={meeting.rejection_reason} />
            </div>
          ) : null}
        </CardContent>
      </Card>

      {showApprovalActions ? (
        <Card>
          <CardHeader>
            <CardTitle>Your decision</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-2">
            <Button onClick={onApprove} disabled={decideApproval.isPending}>
              Approve
            </Button>
            <Button variant="destructive" onClick={() => setRejectOpen(true)}>
              Reject…
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {showReschedule ? (
        <Card>
          <CardHeader>
            <CardTitle>Reschedule</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <p className="text-sm text-muted-foreground">
              This request was rejected. Rescheduling resets it to PENDING and
              re-notifies the manager.
            </p>
            <form
              className="grid gap-3 md:grid-cols-4"
              onSubmit={(event) => {
                event.preventDefault();
                const data = new FormData(event.currentTarget);
                const payload = {};
                for (const key of ["meeting_date", "start_time", "end_time", "location"]) {
                  const value = data.get(key)?.toString().trim();
                  if (value) payload[key] = value;
                }
                reschedule.mutateAsync(payload);
              }}
            >
              <Input name="meeting_date" type="date" aria-label="New date" />
              <Input name="start_time" type="time" aria-label="New start" />
              <Input name="end_time" type="time" aria-label="New end" />
              <Button type="submit" disabled={reschedule.isPending}>
                {reschedule.isPending ? "Saving…" : "Reschedule"}
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Participants</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {meeting.participant_details?.length ? (
            <div className="divide-y rounded-lg border">
              {meeting.participant_details.map((participant) => (
                <div key={participant.participant_id} className="flex items-center justify-between gap-3 px-3 py-2.5">
                  <div className="min-w-0"><strong className="block truncate text-sm">{participant.name}</strong><span className="block truncate text-xs text-muted-foreground">{participant.email || "No email"} · {participant.role}</span></div>
                  {can("delete_meetingparticipant") ? <Button type="button" variant="ghost" size="sm" className="text-destructive" disabled={removeParticipant.isPending} onClick={() => removeParticipant.mutateAsync(participant.user_id)}>Remove</Button> : null}
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-muted-foreground">No participants have been added.</p>}
          <p className="text-sm text-muted-foreground">
            The API doesn't expose the participant roster — manage by user UUID.
          </p>
          {can("add_meetingparticipant") ? (
            <form
              className="flex items-end gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (!participantId.trim()) return;
                addParticipant
                  .mutateAsync({
                    user_id: participantId.trim(),
                    participant_role: "Attendee",
                    is_required: true,
                  })
                  .then(() => setParticipantId(""));
              }}
            >
              <div className="flex-1">
                <FormField id="participant_user" label="Add participant">
                  <Select value={participantId} onValueChange={setParticipantId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select user to invite…" />
                    </SelectTrigger>
                    <SelectContent>
                      {users.map((u) => (
                        <SelectItem key={u.user_id} value={String(u.user_id)}>
                          {u.full_name || u.username} {u.role ? `(${u.role})` : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
              </div>
              <Button type="submit" disabled={!participantId.trim() || addParticipant.isPending}>
                Add
              </Button>
            </form>
          ) : null}
          {can("delete_meetingparticipant") ? (
            <form
              className="flex items-end gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (!removeId.trim()) return;
                removeParticipant.mutateAsync(removeId.trim()).then(() => setRemoveId(""));
              }}
            >
              <div className="flex-1">
                <FormField id="participant_remove" label="Remove participant (user UUID)">
                  <Input
                    id="participant_remove"
                    placeholder="00000000-0000-4000-8000-…"
                    value={removeId}
                    onChange={(event) => setRemoveId(event.target.value)}
                  />
                </FormField>
              </div>
              <Button type="submit" variant="outline" disabled={!removeId.trim() || removeParticipant.isPending}>
                Remove
              </Button>
            </form>
          ) : null}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={rejectOpen}
        onOpenChange={setRejectOpen}
        title="Reject this meeting request?"
        description="The requester will be notified and may reschedule."
        confirmLabel="Reject"
        destructive
        loading={decideApproval.isPending}
        onConfirm={() => onReject()}
      >
        <FormField
          id="rejection_reason"
          label="Reason (required)"
          error={rejectionForm.formState.errors.rejection_reason?.message}
        >
          <textarea
            id="rejection_reason"
            rows={3}
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm"
            {...rejectionForm.register("rejection_reason")}
          />
        </FormField>
      </ConfirmDialog>
    </div>
  );
}
