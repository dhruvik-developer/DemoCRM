import { useMemo, useState } from "react";
import {
  Building2,
  CheckCircle2,
  Link2,
  Mail,
  MoreVertical,
  Phone,
  RotateCcw,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useUsers } from "@/features/admin/hooks";
import { useCreateRecordNote, useRecordNotes } from "@/features/notes/hooks";
import { useTasks } from "@/features/tasks/hooks";
import { useAssignTask } from "@/features/tasks/hooks";
import { useFollowUp, useUpdateFollowUp, useUpdateFollowUpStatus, useDeleteFollowUp, useFollowUps } from "../hooks";
import { followUpStatusName, followUpTypeName } from "@/utils/followUpMasterData";

const toDatetimeLocal = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

export default function FollowUpDetail({
  followUp,
  onClose,
  variant = "modal",
  returnLeadId,
}) {
  const navigate = useNavigate();
  const followUpId = followUp?.followup_id;
  const detail = useFollowUpFollowUp(followUpId);
  const taskId = detail?.task_id ?? followUp?.task_id;
  const leadId = detail?.lead_id;
  const status = detail?.followup_status ?? followUp?.followup_status;
  const type = detail?.followup_type ?? followUp?.followup_type;
  const taskTitle = detail?.task_title ?? followUp?.task_title;
  const followupDate = detail?.followup_date ?? followUp?.followup_date;

  const updateStatus = useUpdateFollowUpStatus();
  const updateFollowUp = useUpdateFollowUp();
  const deleteFollowUp = useDeleteFollowUp();
  const assignTask = useAssignTask(taskId);

  const [rescheduling, setRescheduling] = useState(false);
  const [newDate, setNewDate] = useState("");
  const [reassigning, setReassigning] = useState(false);
  const [assignee, setAssignee] = useState("");

  const openTasks = useLeadOpenTasks(leadId);
  const openFollowUps = useLeadOpenFollowUps(leadId);

  const goBack = () => {
    if (returnLeadId) navigate(`/leads/${returnLeadId}`);
    else navigate(-1);
  };

  const saveReschedule = async () => {
    if (!newDate) return;
    await updateFollowUp.mutateAsync({
      followUpId,
      followup_date: new Date(newDate).toISOString(),
      followup_status: 1,
    });
    setRescheduling(false);
    setNewDate("");
  };

  const confirmReassign = async () => {
    if (!assignee) return;
    await assignTask.mutateAsync(assignee);
    setReassigning(false);
    setAssignee("");
  };

  const confirmDelete = async () => {
    await deleteFollowUp.mutateAsync(followUpId);
    if (variant === "page") {
      if (returnLeadId) navigate(`/leads/${returnLeadId}`);
      else navigate(-1);
    } else {
      onClose?.();
    }
  };

  const header = (
    <div className="flex items-start justify-between gap-4">
      <div className="flex min-w-0 items-center gap-3">
        {variant === "page" ? (
          <Button variant="ghost" size="icon-sm" onClick={goBack} title="Close" aria-label="Close follow-up">
            <X className="size-5" />
          </Button>
        ) : null}
        <div className="min-w-0">
          <p className="truncate text-base font-semibold">{taskTitle || `Follow-up #${followUpId}`}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <Badge variant="outline">{followUpTypeName(type)}</Badge>
            <Badge variant={Number(status) === 2 ? "default" : "secondary"}>{followUpStatusName(status)}</Badge>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" title="More actions"><MoreVertical /></Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={() => { setNewDate(toDatetimeLocal(followupDate)); setRescheduling(true); }} disabled={Number(status) === 2}>
              <RotateCcw className="size-4" /> Reschedule
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setReassigning(true)}>
              <UserRound className="size-4" /> Reassign
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive" onSelect={confirmDelete} disabled={deleteFollowUp.isPending}>
              <Trash2 className="size-4" /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <Button
          size="sm"
          className="bg-[#2563EB] hover:bg-[#1D4ED8]"
          disabled={Number(status) === 2 || updateStatus.isPending}
          onClick={() => updateStatus.mutateAsync({ followUpId, statusId: 2 })}
        >
          <CheckCircle2 className="size-4" />
          {Number(status) === 2 ? "Completed" : "Mark complete"}
        </Button>
      </div>
    </div>
  );

  const body = (
    <div className="grid gap-0 overflow-hidden lg:grid-cols-[1fr_300px]">
      <div className="space-y-5 overflow-y-auto p-6">
        <InfoCard title="Follow-up details">
          <InfoRow label="Type" value={followUpTypeName(type)} />
          <InfoRow label="Status" value={followUpStatusName(status)} />
          <InfoRow label="When" value={followupDate ? new Date(followupDate).toLocaleString() : "—"} />
          <InfoRow label="Owner" value={detail?.assigned_to_name || "Unassigned"} />
          <InfoRow label="Created by" value={detail?.created_by_name || "—"} />
        </InfoCard>

        <section className="rounded-xl border bg-card p-4">
          <h3 className="mb-2 text-sm font-semibold">Purpose</h3>
          <p className="whitespace-pre-wrap text-sm text-muted-foreground">{detail?.decription || "No purpose added."}</p>
        </section>

        <section className="rounded-xl border bg-card p-4">
          <h3 className="mb-2 text-sm font-semibold">Outcome</h3>
          <Button
            variant={Number(status) === 2 ? "outline" : "default"}
            disabled={Number(status) === 2 || updateStatus.isPending}
            onClick={() => updateStatus.mutateAsync({ followUpId, statusId: 2 })}
          >
            <CheckCircle2 className="size-4" /> Mark as completed
          </Button>
          {Number(status) === 2 ? <p className="mt-2 text-xs text-muted-foreground">This follow-up is completed.</p> : null}
        </section>

        {rescheduling ? (
          <section className="rounded-xl border border-primary/30 bg-card p-4">
            <h3 className="mb-2 text-sm font-semibold">Reschedule follow-up</h3>
            <div className="flex flex-col gap-2">
              <Input type="datetime-local" value={newDate} onChange={(e) => setNewDate(e.target.value)} />
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => { setRescheduling(false); setNewDate(""); }}>Cancel</Button>
                <Button size="sm" disabled={!newDate || updateFollowUp.isPending} onClick={saveReschedule}>
                  {updateFollowUp.isPending ? "Saving…" : "Save reschedule"}
                </Button>
              </div>
            </div>
          </section>
        ) : null}

        {reassigning ? (
          <section className="rounded-xl border border-primary/30 bg-card p-4">
            <h3 className="mb-2 text-sm font-semibold">Reassign task</h3>
            <ReassignForm assignee={assignee} setAssignee={setAssignee} onCancel={() => setReassigning(false)} onConfirm={confirmReassign} pending={assignTask.isPending} />
          </section>
        ) : null}

        <NotesSection type="followup" id={followUpId} />
      </div>

      <aside className="space-y-5 border-t border-border p-6 lg:border-l lg:border-t-0">
        <section className="rounded-xl border bg-card p-4">
          <h3 className="mb-3 text-sm font-semibold">Contact</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-muted text-lg font-semibold">
                {(detail?.lead_name || "?").charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{detail?.lead_name || "Unknown lead"}</p>
                {detail?.lead_company ? <p className="truncate text-xs text-muted-foreground">{detail.lead_company}</p> : null}
              </div>
            </div>
            {detail?.lead_email ? (
              <p className="flex items-center gap-2 text-sm text-muted-foreground"><Mail className="size-4 shrink-0" /> <span className="truncate">{detail.lead_email}</span></p>
            ) : null}
            {detail?.lead_phone ? (
              <p className="flex items-center gap-2 text-sm text-muted-foreground"><Phone className="size-4 shrink-0" /> {detail.lead_phone}</p>
            ) : null}
            {detail?.lead_id ? (
              <Button asChild variant="outline" size="sm" className="w-full">
                <Link to={`/leads/${detail.lead_id}`}><Link2 className="size-4" /> View lead</Link>
              </Button>
            ) : null}
          </div>
        </section>

        <section className="rounded-xl border bg-card p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold"><Building2 className="size-4" /> Open activities</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Open tasks</span>
              <span className="font-semibold">{openTasks.isLoading ? "…" : openTasks.count}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Pending follow-ups</span>
              <span className="font-semibold">{openFollowUps.isLoading ? "…" : openFollowUps.count}</span>
            </div>
          </div>
        </section>
      </aside>
    </div>
  );

  if (variant === "page") {
    return (
      <div className="mx-auto flex h-dvh max-w-6xl flex-col">
        <header className="flex items-center justify-between border-b px-6 py-4">
          <div className="min-w-0">{header}</div>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto">{body}</div>
      </div>
    );
  }

  return (
    <Dialog open={Boolean(followUp)} onOpenChange={(open) => !open && onClose?.()}>
      <DialogContent className="left-auto right-0 top-0 h-dvh w-full max-w-3xl translate-x-0 translate-y-0 content-start gap-0 rounded-none p-0 sm:max-w-3xl" showCloseButton>
        <DialogHeader className="border-b px-6 py-5">{header}</DialogHeader>
        <div className="min-h-0 flex-1">{body}</div>
      </DialogContent>
    </Dialog>
  );
}

function useFollowUpFollowUp(followUpId) {
  const query = useFollowUp(followUpId);
  return query.data;
}

function useLeadOpenTasks(leadId) {
  const query = useTasks({ lead: leadId, page_size: 100 }, { enabled: Boolean(leadId) });
  const count = useMemo(
    () => (query.data?.results ?? []).filter((task) => Number(task.status) !== 3).length,
    [query.data],
  );
  return { count, isLoading: query.isLoading };
}

function useLeadOpenFollowUps(leadId) {
  const query = useFollowUps({ lead: leadId, page_size: 100 }, { enabled: Boolean(leadId) });
  const count = useMemo(
    () => (query.data?.results ?? []).filter((f) => Number(f.followup_status) !== 2).length,
    [query.data],
  );
  return { count, isLoading: query.isLoading };
}

function InfoCard({ title, children }) {
  return (
    <section className="rounded-xl border bg-card p-4">
      <h3 className="mb-2 text-sm font-semibold">{title}</h3>
      <div className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">{children}</div>
    </section>
  );
}

function InfoRow({ label, value }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="truncate">{value || "—"}</p>
    </div>
  );
}

function ReassignForm({ assignee, setAssignee, onCancel, onConfirm, pending }) {
  const usersQuery = useUsers();
  return (
    <div className="flex flex-col gap-3">
      <Select value={assignee} onValueChange={setAssignee}>
        <SelectTrigger><SelectValue placeholder="Select employee" /></SelectTrigger>
        <SelectContent>
          {(usersQuery.data ?? []).map((user) => (
            <SelectItem key={user.user_id} value={user.user_id}>
              {user.full_name || user.username} {user.role ? `(${user.role})` : ""}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel}>Cancel</Button>
        <Button size="sm" disabled={!assignee || pending || usersQuery.isLoading} onClick={onConfirm}>
          {pending ? "Assigning…" : "Reassign"}
        </Button>
      </div>
    </div>
  );
}

function NotesSection({ type, id }) {
  const [body, setBody] = useState("");
  const notesQuery = useRecordNotes(type, id);
  const createNote = useCreateRecordNote(type, id);
  const notes = notesQuery.data ?? [];

  const submit = async (event) => {
    event.preventDefault();
    if (!body.trim()) return;
    await createNote.mutateAsync(body.trim());
    setBody("");
  };

  return (
    <section className="rounded-xl border bg-card p-4">
      <h3 className="mb-3 text-sm font-semibold">Notes <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{notes.length}</span></h3>
      <form onSubmit={submit} className="mb-4 flex gap-2">
        <Textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder="Add a note" rows={2} maxLength={5000} />
        <Button type="submit" disabled={!body.trim() || createNote.isPending}>{createNote.isPending ? "Adding…" : "Add"}</Button>
      </form>
      <div className="max-h-64 space-y-3 overflow-y-auto">
        {notesQuery.isLoading ? <p className="text-sm text-muted-foreground">Loading notes…</p> : null}
        {notesQuery.isError ? <p className="text-sm text-destructive">Could not load notes.</p> : null}
        {!notesQuery.isLoading && !notes.length ? <p className="py-6 text-center text-sm text-muted-foreground">No notes yet.</p> : null}
        {notes.map((note) => (
          <article key={note.note_id} className="rounded-xl border bg-muted/50 p-3">
            <div className="mb-1 flex items-center justify-between gap-3 text-xs text-muted-foreground">
              <strong className="text-foreground">{note.author_name}</strong>
              <time>{new Date(note.created_at).toLocaleString()}</time>
            </div>
            <p className="whitespace-pre-wrap text-sm">{note.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
