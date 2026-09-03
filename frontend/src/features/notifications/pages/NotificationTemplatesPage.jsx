// Notification templates admin (Manager/Admin only via view/add/
// delete_notificationtemplate) + manual notification send. Event types are
// free-text-with-suggestions since the backend enum has 40+ values.

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import {
  useCreateNotificationTemplate,
  useDeleteNotificationTemplate,
  useNotificationTemplates,
  useSendManualNotification,
} from "../hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import FormField from "@/components/forms/FormField";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const templateSchema = z.object({
  name: z.string().trim().min(1, "Name is required."),
  event_type: z.string().trim().min(1, "Event type is required."),
  message: z.string().trim().min(1, "Message is required."),
  channel: z.enum(["IN_APP", "EMAIL", "BOTH"]),
});

const sendSchema = z
  .object({
    recipient_ids: z.string().trim().min(1, "At least one recipient UUID is required."),
    event_type: z.string().trim().optional().or(z.literal("")),
    custom_message: z.string().trim().optional().or(z.literal("")),
    channel: z.enum(["IN_APP", "EMAIL", "BOTH"]),
  });

function CreateTemplateDialog({ open, onOpenChange }) {
  const createTemplate = useCreateNotificationTemplate();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(templateSchema),
    defaultValues: { name: "", event_type: "", message: "", channel: "IN_APP" },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New template</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit((values) => createTemplate.mutateAsync(values).then(() => onOpenChange(false)))} className="flex flex-col gap-3">
          <FormField id="tpl_name" label="Name" error={errors.name?.message}>
            <Input id="tpl_name" {...register("name")} />
          </FormField>
          <FormField id="tpl_event" label="Event type" error={errors.event_type?.message}
            help="e.g. TASK_ASSIGNED, MEETING_CREATED, QUOTATION_SENT…"
          >
            <Input id="tpl_event" {...register("event_type")} />
          </FormField>
          <FormField id="tpl_message" label="Message"
            help="Placeholders like {{lead_name}} are replaced server-side."
            error={errors.message?.message}
          >
            <Textarea id="tpl_message" rows={3} {...register("message")} />
          </FormField>
          <FormField id="tpl_channel" label="Channel">
            <select
              id="tpl_channel"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              {...register("channel")}
            >
              <option value="IN_APP">In-app</option>
              <option value="EMAIL">Email</option>
              <option value="BOTH">Both</option>
            </select>
          </FormField>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={createTemplate.isPending}>
              {createTemplate.isPending ? "Saving…" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function SendDialog({ open, onOpenChange }) {
  const send = useSendManualNotification();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(sendSchema),
    defaultValues: { recipient_ids: "", event_type: "", custom_message: "", channel: "IN_APP" },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Send notification</DialogTitle>
        </DialogHeader>
        {/* G6: recipients by UUID — a user picker needs GET /users/. */}
        <form
          onSubmit={handleSubmit((values) =>
            send
              .mutateAsync({
                recipient_ids: values.recipient_ids.split(",").map((id) => id.trim()).filter(Boolean),
                event_type: values.event_type || undefined,
                custom_message: values.custom_message || undefined,
                channel: values.channel,
              })
              .then(() => onOpenChange(false)),
          )}
          className="flex flex-col gap-3"
        >
          <FormField
            id="recipients"
            label="Recipient UUIDs (comma-separated)"
            error={errors.recipient_ids?.message}
          >
            <Textarea id="recipients" rows={2} {...register("recipient_ids")} />
          </FormField>
          <FormField id="send_event" label="Event type (default MANUAL)">
            <Input id="send_event" placeholder="MANUAL" {...register("event_type")} />
          </FormField>
          <FormField id="send_message" label="Custom message">
            <Textarea id="send_message" rows={2} {...register("custom_message")} />
          </FormField>
          <FormField id="send_channel" label="Channel">
            <select
              id="send_channel"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              {...register("channel")}
            >
              <option value="IN_APP">In-app</option>
              <option value="EMAIL">Email</option>
              <option value="BOTH">Both</option>
            </select>
          </FormField>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={send.isPending}>
              {send.isPending ? "Sending…" : "Send"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function NotificationTemplatesPage() {
  const templatesQuery = useNotificationTemplates({});
  const deleteTemplate = useDeleteNotificationTemplate();

  const [createOpen, setCreateOpen] = useState(false);
  const [sendOpen, setSendOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);

  const rawRows = templatesQuery.data?.results ?? templatesQuery.data ?? [];
  const rows = (Array.isArray(rawRows) ? rawRows : []).filter(Boolean);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Notification templates</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setSendOpen(true)}>Send notification…</Button>
          <Button onClick={() => setCreateOpen(true)}>New template</Button>
        </div>
      </div>

      {templatesQuery.isError ? (
        <PageError error={templatesQuery.error} onRetry={templatesQuery.refetch} />
      ) : (
        <DataTable
          columns={[
            { key: "name", header: "Name" },
            {
              key: "event_type",
              header: "Event",
              render: (row) => (
                <Badge variant="outline" className="font-mono text-[10px]">{row.event_type}</Badge>
              ),
            },
            {
              key: "channel",
              header: "Channel",
              render: (row) => <Badge variant="secondary">{row.channel}</Badge>,
            },
            {
              key: "is_default",
              header: "Default",
              render: (row) => (row.is_default ? <Badge>default</Badge> : null),
            },
            {
              key: "is_active",
              header: "Active",
              render: (row) => (row.is_active ? "Yes" : "No"),
            },
            {
              key: "actions",
              header: "",
              render: (row) =>
                row.is_active ? (
                  <div className="text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive"
                      onClick={() => setPendingDelete(row)}
                    >
                      Deactivate
                    </Button>
                  </div>
                ) : null,
            },
          ]}
          rows={rows}
          getRowId={(row) => row?.id ?? String(row?.name ?? Math.random())}
          isLoading={templatesQuery.isLoading}
          emptyState={<EmptyState title="No templates yet" description="Templates render messages for workflow events." />}
          page={1}
          pageSize={Math.max(rows.length, 1)}
          count={rows.length}
        />
      )}

      <CreateTemplateDialog open={createOpen} onOpenChange={setCreateOpen} />
      <SendDialog open={sendOpen} onOpenChange={setSendOpen} />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title={`Deactivate "${pendingDelete?.name}"?`}
        description="Deactivation is soft — the template stays in the database but stops being used."
        confirmLabel="Deactivate"
        destructive
        loading={deleteTemplate.isPending}
        onConfirm={() =>
          pendingDelete?.id
            ? deleteTemplate.mutateAsync(pendingDelete.id).then(() => setPendingDelete(null))
            : Promise.resolve()
        }
      />
    </div>
  );
}
