import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";

import {
  useCallTemplates,
  useDeleteCallTemplate,
  useUpdateCallTemplate,
} from "@/features/callforms/hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import FormField from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MEETING_TEMPLATE_MARKER, meetingTemplateDescription, meetingTemplateType } from "../templateUtils";

export default function MeetingTemplatesPage() {
  const navigate = useNavigate();
  const templatesQuery = useCallTemplates();
  const updateTemplate = useUpdateCallTemplate();
  const deleteTemplate = useDeleteCallTemplate();
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const editForm = useForm({ defaultValues: { name: "", template_type: "online", is_active: true } });

  const rows = (templatesQuery.data ?? []).filter(
    (template) => template?.description?.startsWith(MEETING_TEMPLATE_MARKER),
  );

  const startEdit = (template) => {
    setEditing(template);
    editForm.reset({ name: template.name, template_type: meetingTemplateType(template), is_active: template.is_active ?? true });
  };

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Meeting templates</h1>
          <p className="text-sm text-muted-foreground">Build versioned, fully dynamic fields for meeting forms.</p>
        </div>
        <Button asChild>
          <Link to="/meeting-templates/new">New template</Link>
        </Button>
      </div>

      {templatesQuery.isError ? <PageError error={templatesQuery.error} onRetry={templatesQuery.refetch} /> : (
        <DataTable
          columns={[
            { key: "name", header: "Name" },
            { key: "template_type", header: "Type", render: (row) => <span className="capitalize">{meetingTemplateType(row)}</span> },
            { key: "is_active", header: "Active", render: (row) => row.is_active ? "Yes" : "No" },
            { key: "actions", header: "Actions", render: (row) => (
              <div className="flex gap-2">
                <Button size="sm" onClick={() => navigate(`/meeting-templates/${row.id}`)}>Build fields</Button>
                <Button size="sm" variant="outline" onClick={() => startEdit(row)}>Edit</Button>
                <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setDeleting(row)}>Delete</Button>
              </div>
            )},
          ]}
          rows={rows}
          getRowId={(row) => row.id}
          isLoading={templatesQuery.isLoading}
          emptyState={<EmptyState title="No meeting templates yet" description="Create a template, then add fields to it." />}
          page={1}
          pageSize={Math.max(rows.length, 1)}
          count={rows.length}
        />
      )}

      <Dialog open={Boolean(editing)} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent><DialogHeader><DialogTitle>Edit meeting template</DialogTitle></DialogHeader>
          <form className="flex flex-col gap-4" onSubmit={editForm.handleSubmit((values) => updateTemplate.mutateAsync({ id: editing.id, name: values.name, is_active: values.is_active, description: meetingTemplateDescription(values.template_type) }).then(() => setEditing(null)))}>
            <FormField id="edit_meeting_template_name" label="Name"><Input {...editForm.register("name")} /></FormField>
            <FormField id="edit_meeting_template_type" label="Meeting workflow"><Select value={editForm.watch("template_type")} onValueChange={(value) => editForm.setValue("template_type", value)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="online">Online meeting</SelectItem><SelectItem value="offline">Offline meeting</SelectItem><SelectItem value="reschedule">Reschedule request</SelectItem></SelectContent></Select></FormField>
            <label className="flex gap-2 text-sm"><input type="checkbox" {...editForm.register("is_active")} /> Active</label>
            <DialogFooter><Button type="button" variant="outline" onClick={() => setEditing(null)}>Cancel</Button><Button type="submit">Save</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {deleting ? (
        <ConfirmDialog open onOpenChange={(open) => !open && setDeleting(null)} title={`Delete "${deleting.name}"?`} description="This removes all versions and fields." confirmLabel="Delete" destructive onConfirm={() => deleteTemplate.mutateAsync(deleting.id).then(() => setDeleting(null))} />
      ) : null}
    </div>
  );
}
