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
  useUpdateNotificationTemplate,
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
  is_default: z.boolean(),
});

const MEETING_TEMPLATE_EVENTS = [
  ["ONLINE_MEETING_CREATED", "Online meeting"],
  ["OFFLINE_MEETING_CREATED", "Offline meeting"],
  ["MEETING_CREATED", "Custom meeting"],
  ["MEETING_APPROVED", "Meeting approved"],
  ["MEETING_REJECTED", "Meeting rejected"],
  ["MEETING_RESCHEDULED", "Meeting rescheduled"],
];

const DYNAMIC_FIELDS = [
  "manager_name",
  "employee_name",
  "meeting_title",
  "meeting_date",
  "start_time",
  "end_time",
  "meeting_link",
  "location",
];

function DynamicFieldPicker({ onInsert }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {DYNAMIC_FIELDS.map((field) => (
        <Button key={field} type="button" variant="outline" size="sm" onClick={() => onInsert(`{{${field}}}`)}>
          {field.replaceAll("_", " ")}
        </Button>
      ))}
    </div>
  );
}

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
    getValues,
    setValue,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(templateSchema),
    defaultValues: { name: "", event_type: "ONLINE_MEETING_CREATED", message: "", channel: "BOTH", is_default: true },
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
          <FormField id="tpl_event" label="Meeting template type" error={errors.event_type?.message}
            help="e.g. TASK_ASSIGNED, MEETING_CREATED, QUOTATION_SENT…"
          >
            <select
              id="tpl_event"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              {...register("event_type")}
            >
              {MEETING_TEMPLATE_EVENTS.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </FormField>
          <FormField id="tpl_message" label="Message"
            help="Placeholders like {{lead_name}} are replaced server-side."
            error={errors.message?.message}
          >
            <Textarea id="tpl_message" rows={3} {...register("message")} />
          </FormField>
          <DynamicFieldPicker
            onInsert={(placeholder) =>
              setValue("message", `${getValues("message") || ""}${getValues("message") ? " " : ""}${placeholder}`)
            }
          />
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
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...register("is_default")} />
            Use automatically as the default for this meeting type
          </label>
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

function EditTemplateDialog({ template, onOpenChange }) {
  const updateTemplate = useUpdateNotificationTemplate();
  const form = useForm({
    resolver: zodResolver(templateSchema),
    defaultValues: {
      name: template?.name ?? "",
      event_type: template?.event_type ?? "ONLINE_MEETING_CREATED",
      message: template?.message ?? "",
      channel: template?.channel ?? "BOTH",
      is_default: template?.is_default ?? false,
    },
  });

  return (
    <Dialog open={Boolean(template)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Edit meeting template</DialogTitle></DialogHeader>
        <form
          className="flex flex-col gap-3"
          onSubmit={form.handleSubmit((values) =>
            updateTemplate.mutateAsync({ templateId: template.id, ...values }).then(() => onOpenChange(false)),
          )}
        >
          <FormField id="edit_tpl_name" label="Name" error={form.formState.errors.name?.message}>
            <Input id="edit_tpl_name" {...form.register("name")} />
          </FormField>
          <FormField id="edit_tpl_event" label="Meeting template type">
            <select id="edit_tpl_event" className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm" {...form.register("event_type")}>
              {MEETING_TEMPLATE_EVENTS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </FormField>
          <FormField id="edit_tpl_message" label="Message" error={form.formState.errors.message?.message}>
            <Textarea id="edit_tpl_message" rows={5} {...form.register("message")} />
          </FormField>
          <DynamicFieldPicker onInsert={(placeholder) => form.setValue("message", `${form.getValues("message") || ""}${form.getValues("message") ? " " : ""}${placeholder}`)} />
          <FormField id="edit_tpl_channel" label="Channel">
            <select id="edit_tpl_channel" className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm" {...form.register("channel")}>
              <option value="IN_APP">In-app</option><option value="EMAIL">Email</option><option value="BOTH">Both</option>
            </select>
          </FormField>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...form.register("is_default")} /> Use automatically as default</label>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={updateTemplate.isPending}>{updateTemplate.isPending ? "Saving…" : "Save changes"}</Button>
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
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);

  const templateData = templatesQuery.data?.results ?? templatesQuery.data;
  const rows = (Array.isArray(templateData) ? templateData : []).filter(
    (template) =>
      template?.id != null &&
      MEETING_TEMPLATE_EVENTS.some(([eventType]) => eventType === template.event_type),
  );

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Meeting templates</h1>
          <p className="text-sm text-muted-foreground">Build dynamic email and notification layouts for every meeting type.</p>
        </div>
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
              header: "Actions",
              render: (row) =>
                row.is_active ? (
                  <div className="flex items-center gap-2">
                    <Button size="sm" variant="outline" onClick={() => setEditingTemplate(row)}>
                      Edit
                    </Button>
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
          getRowId={(row) => row?.id ?? `${row?.event_type}-${row?.name}`}
          isLoading={templatesQuery.isLoading}
          emptyState={<EmptyState title="No templates yet" description="Templates render messages for workflow events." />}
          page={1}
          pageSize={Math.max(rows.length, 1)}
          count={rows.length}
        />
      )}

      {createOpen ? <CreateTemplateDialog open onOpenChange={setCreateOpen} /> : null}
      {editingTemplate ? (
        <EditTemplateDialog
          key={editingTemplate.id}
          template={editingTemplate}
          onOpenChange={(open) => !open && setEditingTemplate(null)}
        />
      ) : null}
      {sendOpen ? <SendDialog open onOpenChange={setSendOpen} /> : null}

      {pendingDelete ? <ConfirmDialog
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
      /> : null}
    </div>
  );
}
