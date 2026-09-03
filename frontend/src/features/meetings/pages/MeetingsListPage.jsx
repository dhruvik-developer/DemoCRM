import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { useMeetings, useDecideApproval, useRescheduleMeeting, useMeetingKpi } from "../hooks";
import { useUsers } from "@/features/admin/hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import FormField from "@/components/forms/FormField";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import ListControls from "@/components/common/ListControls";
import { usePinnedRecords } from "@/hooks/usePinnedRecords";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Video, Check, X, CalendarClock, MessageSquareText, Pin, ListTodo, Hourglass, CheckCircle2, XCircle, Monitor, Building2, CalendarCheck2, CalendarRange } from "lucide-react";
import RecordNotesPanel from "@/features/notes/components/RecordNotesPanel";

function KpiCard({ title, value, loading, icon: Icon, to }) {
  return (
    <Card className="rounded-xl">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-7 w-12" /> : <div className="text-2xl font-bold">{value ?? "—"}</div>}
        {to ? <Link to={to} className="text-xs text-[#2563EB] hover:underline">View →</Link> : null}
      </CardContent>
    </Card>
  );
}

export default function MeetingsListPage() {
  const { user, resolved } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const usersQuery = useUsers();
  const decideApproval = useDecideApproval();
  const reschedule = useRescheduleMeeting();
  const kpi = useMeetingKpi();

  const [rejectMeeting, setRejectMeeting] = useState(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [reschedulingMeeting, setReschedulingMeeting] = useState(null);
  const [newDate, setNewDate] = useState("");
  const [newStart, setNewStart] = useState("");
  const [newEnd, setNewEnd] = useState("");
  const [notesRecord, setNotesRecord] = useState(null);

  const page = Number(searchParams.get("page") ?? "1");
  const search = searchParams.get("search") ?? "";
  const approvalFilter = searchParams.get("approval") ?? "all"; // all | PENDING | APPROVED | REJECTED
  const ordering = searchParams.get("ordering") ?? "";
  const pinnedOnly = searchParams.get("pinned") === "1";
  const pins = usePinnedRecords("crm:pinned-meetings");

  // Manager check using resolved.roleName set by resolvePermissions
  const isManagerRole =
    resolved?.isAdmin ||
    resolved?.roleName === "Manager" ||
    String(resolved?.roleName || "").toLowerCase() === "manager";

  const updateParam = (key, value) => {
    setSearchParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (value) {
          next.set(key, value);
        } else {
          next.delete(key);
        }
        if (key !== "page") {
          next.delete("page");
        }
        return next;
      },
      { replace: true },
    );
  };

  const meetingsQuery = useMeetings({
    page: pinnedOnly ? 1 : page,
    page_size: pinnedOnly ? 100 : 10,
    search: search || undefined,
    approval_status: approvalFilter !== "all" ? approvalFilter : undefined,
    ordering: ordering || undefined,
  });

  let rows = meetingsQuery.data?.results ?? [];
  if (pinnedOnly) rows = rows.filter((meeting) => pins.isPinned(meeting.meeting_id));
  rows = pins.pinnedFirst(rows, (meeting) => meeting.meeting_id);
  const count = pinnedOnly ? rows.length : (meetingsQuery.data?.count ?? 0);
  // Only Manager or Admin can create/schedule meetings — Employee cannot
  const canCreate = hasPermission(resolved, "add_meeting");

  const findUserName = (userId) => {
    if (!userId) return "—";
    if (typeof userId === "object") {
      return userId.full_name || userId.username || userId.email;
    }
    const found = (usersQuery.data ?? []).find(
      (u) => String(u.user_id) === String(userId),
    );
    return found?.full_name || found?.username || `${String(userId).slice(0, 8)}…`;
  };

  const getApprovalBadge = (status) => {
    const s = String(status || "").toUpperCase();
    if (s === "APPROVED") {
      return (
        <Badge className="bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/25 dark:text-emerald-300 border-emerald-500/30">
          Approved
        </Badge>
      );
    }
    if (s === "REJECTED") {
      return <Badge variant="destructive">Rejected</Badge>;
    }
    return (
      <Badge className="bg-amber-500/15 text-amber-700 hover:bg-amber-500/25 dark:text-amber-300 border-amber-500/30">
        Pending Approval
      </Badge>
    );
  };

  const handleApprove = async (meeting) => {
    await decideApproval.mutateAsync({
      meetingId: meeting.meeting_id,
      decision: "APPROVE",
      approval_status: "APPROVED",
    });
  };

  const handleRejectSubmit = async (e) => {
    e.preventDefault();
    if (!rejectMeeting || !rejectionReason.trim()) return;
    await decideApproval.mutateAsync({
      meetingId: rejectMeeting.meeting_id,
      decision: "REJECT",
      approval_status: "REJECTED",
      rejection_reason: rejectionReason.trim(),
    });
    setRejectMeeting(null);
    setRejectionReason("");
  };

  const handleRescheduleSubmit = async (e) => {
    e.preventDefault();
    if (!reschedulingMeeting || !newDate || !newStart || !newEnd) return;
    await reschedule.mutateAsync({
      meetingId: reschedulingMeeting.meeting_id,
      meeting_date: newDate,
      start_time: newStart,
      end_time: newEnd,
    });
    setReschedulingMeeting(null);
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Meetings</h1>
          <p className="text-sm text-muted-foreground">
            Manage scheduled meetings, manager approval decisions, and meeting invites.
          </p>
        </div>
        {canCreate ? (
          <Button asChild className="bg-secondary hover:bg-[#E0532A]">
            <Link to="/meetings/new">Schedule Meeting</Link>
          </Button>
        ) : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard title="Total meetings" value={kpi.data?.total} loading={kpi.isLoading} icon={ListTodo} />
        <KpiCard title="Pending approval" value={kpi.data?.pending} loading={kpi.isLoading} icon={Hourglass} to="/meetings?approval=PENDING" />
        <KpiCard title="Approved" value={kpi.data?.approved} loading={kpi.isLoading} icon={CheckCircle2} to="/meetings?approval=APPROVED" />
        <KpiCard title="Rejected" value={kpi.data?.rejected} loading={kpi.isLoading} icon={XCircle} to="/meetings?approval=REJECTED" />
        <KpiCard title="Online" value={kpi.data?.online} loading={kpi.isLoading} icon={Monitor} />
        <KpiCard title="Offline" value={kpi.data?.offline} loading={kpi.isLoading} icon={Building2} />
        <KpiCard title="Due today" value={kpi.data?.today} loading={kpi.isLoading} icon={CalendarCheck2} />
        <KpiCard title="Upcoming" value={kpi.data?.upcoming} loading={kpi.isLoading} icon={CalendarRange} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {[
          ["all", "All Meetings"],
          ["PENDING", "Pending Approval"],
          ["APPROVED", "Approved"],
          ["REJECTED", "Rejected"],
        ].map(([key, label]) => (
          <Button
            key={key}
            variant={approvalFilter === key ? "default" : "outline"}
            size="sm"
            onClick={() => updateParam("approval", key === "all" ? "" : key)}
            className={approvalFilter === key ? "bg-[#2563EB] hover:bg-[#1D4ED8]" : ""}
          >
            {label}
          </Button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <Input
            placeholder="Search meetings…"
            className="w-64"
            defaultValue={search}
            onChange={(event) => updateParam("search", event.target.value.trim())}
          />
        </div>
        <ListControls
          filterValue={approvalFilter}
          filterOptions={[{ value: "all", label: "All meetings" }, { value: "PENDING", label: "Pending approval" }, { value: "APPROVED", label: "Approved" }, { value: "REJECTED", label: "Rejected" }]}
          onFilterChange={(value) => updateParam("approval", value === "all" ? "" : value)}
          sortValue={ordering}
          sortOptions={[{ value: "meeting_date", label: "Date: oldest first" }, { value: "-meeting_date", label: "Date: newest first" }, { value: "meeting_title", label: "Title: A–Z" }]}
          onSortChange={(value) => updateParam("ordering", value)}
          pinnedOnly={pinnedOnly}
          onPinnedOnlyChange={(value) => updateParam("pinned", value ? "1" : "")}
        />
      </div>

      {meetingsQuery.isError ? (
        <PageError error={meetingsQuery.error} onRetry={meetingsQuery.refetch} />
      ) : (
        <DataTable
          columns={[
            {
              key: "pin",
              header: "",
              className: "w-10",
              render: (meeting) => <Button variant="ghost" size="icon-sm" title={pins.isPinned(meeting.meeting_id) ? "Unpin meeting" : "Pin meeting"} onClick={() => pins.togglePin(meeting.meeting_id)}><Pin className={pins.isPinned(meeting.meeting_id) ? "fill-primary text-primary" : "text-muted-foreground"} /></Button>,
            },
            {
              key: "meeting_title",
              header: "Meeting Title",
              sortable: true,
              render: (meeting) => (
                <div className="flex items-center gap-2">
                  <Link
                    to={`/meetings/${meeting.meeting_id}`}
                    className="font-medium text-foreground hover:underline"
                  >
                    {meeting.meeting_title}
                  </Link>
                  {meeting.meeting_link ? (
                    <a
                      href={meeting.meeting_link}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700 hover:bg-blue-100 dark:bg-blue-950 dark:text-blue-300"
                    >
                      <Video className="size-3" />
                      Join Link
                    </a>
                  ) : null}
                </div>
              ),
            },
            {
              key: "date_time",
              header: "Schedule",
              render: (meeting) => (
                <div className="text-sm">
                  <div>{meeting.meeting_date || "—"}</div>
                  <div className="text-xs text-muted-foreground">
                    {meeting.start_time ? meeting.start_time.slice(0, 5) : ""}
                    {meeting.end_time ? ` – ${meeting.end_time.slice(0, 5)}` : ""}
                  </div>
                </div>
              ),
            },
            {
              key: "approval_status",
              header: "Approval Status",
              render: (meeting) => getApprovalBadge(meeting.approval_status),
            },
            {
              key: "manager",
              header: "Assigned Manager",
              render: (meeting) => findUserName(meeting.manager),
            },
            {
              key: "created_by",
              header: "Requested By",
              render: (meeting) => findUserName(meeting.created_by),
            },
            {
              key: "notes",
              header: "Notes",
              className: "w-16",
              render: (meeting) => <Button variant="ghost" size="icon-sm" title="Add note" aria-label={`Notes for ${meeting.meeting_title}`} onClick={() => setNotesRecord({ type: "meeting", id: meeting.meeting_id, title: meeting.meeting_title })}><MessageSquareText /></Button>,
            },
            {
              key: "actions",
              header: "",
              render: (meeting) => {
                const isPending =
                  String(meeting.approval_status).toUpperCase() === "PENDING" ||
                  meeting.meeting_status === 1;
                const isRejected =
                  String(meeting.approval_status).toUpperCase() === "REJECTED" ||
                  meeting.meeting_status === 4;

                const isAssignedManager =
                  user?.user_id != null &&
                  String(meeting.manager?.user_id ?? meeting.manager ?? "") ===
                    String(user.user_id);

                return (
                  <div className="flex items-center justify-end gap-1.5">
                    {/* Manager Accept / Reject buttons on Pending meetings */}
                    {isPending && (isManagerRole || isAssignedManager) ? (
                      <>
                        <Button
                          size="sm"
                          className="bg-emerald-600 hover:bg-emerald-700 text-white h-8 px-2.5"
                          disabled={decideApproval.isPending}
                          onClick={() => handleApprove(meeting)}
                        >
                          <Check className="mr-1 size-3.5" />
                          Accept
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-destructive hover:bg-destructive/10 h-8 px-2.5"
                          disabled={decideApproval.isPending}
                          onClick={() => {
                            setRejectMeeting(meeting);
                            setRejectionReason("");
                          }}
                        >
                          <X className="mr-1 size-3.5" />
                          Reject
                        </Button>
                      </>
                    ) : null}

                    {/* Employee Reschedule button on Rejected meetings (Employee only) */}
                    {isRejected && !isManagerRole ? (
                      <Button
                        size="sm"
                        className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white h-8 px-2.5"
                        onClick={() => {
                          setReschedulingMeeting(meeting);
                          setNewDate(meeting.meeting_date || "");
                          setNewStart(meeting.start_time ? meeting.start_time.slice(0, 5) : "");
                          setNewEnd(meeting.end_time ? meeting.end_time.slice(0, 5) : "");
                        }}
                      >
                        <CalendarClock className="mr-1 size-3.5" />
                        Reschedule
                      </Button>
                    ) : null}

                    <Button asChild variant="ghost" size="sm" className="h-8">
                      <Link to={`/meetings/${meeting.meeting_id}`}>Open →</Link>
                    </Button>
                  </div>
                );
              },
            },
          ]}
          rows={rows}
          getRowId={(row) => row.meeting_id}
          isLoading={meetingsQuery.isLoading}
          emptyState={
            <EmptyState
              title="No meetings found"
              description={
                search
                  ? "Try adjusting the search or filter."
                  : canCreate
                    ? "Request a meeting to get started."
                    : "No meetings scheduled yet."
              }
              ctaLabel={canCreate && !search ? "Request meeting" : undefined}
              ctaTo={canCreate ? "/meetings/new" : undefined}
            />
          }
          page={pinnedOnly ? 1 : page}
          pageSize={10}
          count={count}
          onPageChange={(nextPage) => updateParam("page", String(nextPage))}
        />
      )}

      {/* Manager Reject Modal */}
      {rejectMeeting && (
        <Dialog open={Boolean(rejectMeeting)} onOpenChange={(open) => !open && setRejectMeeting(null)}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Reject Meeting Request</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleRejectSubmit} className="flex flex-col gap-4">
              <p className="text-sm text-muted-foreground">
                Please provide a reason for rejecting{" "}
                <strong>{rejectMeeting.meeting_title}</strong>. The employee will be notified to reschedule.
              </p>
              <FormField id="rejection_reason" label="Rejection Reason" required>
                <Textarea
                  id="rejection_reason"
                  rows={3}
                  placeholder="e.g. Conflict with client review meeting at 3 PM, please pick another slot."
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  required
                />
              </FormField>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setRejectMeeting(null)}>
                  Cancel
                </Button>
                <Button type="submit" variant="destructive" disabled={!rejectionReason.trim() || decideApproval.isPending}>
                  {decideApproval.isPending ? "Rejecting…" : "Reject Meeting"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}

      {/* Employee Reschedule Modal */}
      {reschedulingMeeting && (
        <Dialog open={Boolean(reschedulingMeeting)} onOpenChange={(open) => !open && setReschedulingMeeting(null)}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Reschedule Meeting</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleRescheduleSubmit} className="flex flex-col gap-4">
              {reschedulingMeeting.rejection_reason ? (
                <div className="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-900 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
                  <strong>Manager Feedback:</strong> {reschedulingMeeting.rejection_reason}
                </div>
              ) : null}

              <FormField id="new_date" label="New Meeting Date" required>
                <Input
                  type="date"
                  value={newDate}
                  onChange={(e) => setNewDate(e.target.value)}
                  required
                />
              </FormField>

              <div className="grid grid-cols-2 gap-3">
                <FormField id="new_start" label="Start Time" required>
                  <Input
                    type="time"
                    value={newStart}
                    onChange={(e) => setNewStart(e.target.value)}
                    required
                  />
                </FormField>
                <FormField id="new_end" label="End Time" required>
                  <Input
                    type="time"
                    value={newEnd}
                    onChange={(e) => setNewEnd(e.target.value)}
                    required
                  />
                </FormField>
              </div>

              <DialogFooter className="mt-2">
                <Button type="button" variant="outline" onClick={() => setReschedulingMeeting(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={!newDate || !newStart || !newEnd || reschedule.isPending}>
                  {reschedule.isPending ? "Rescheduling…" : "Submit New Schedule"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}
      <RecordNotesPanel record={notesRecord} onClose={() => setNotesRecord(null)} />
    </div>
  );
}
