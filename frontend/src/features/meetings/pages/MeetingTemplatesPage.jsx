import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";

import {
  useCallTemplates,
  useCreateCallTemplate,
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

export const MEETING_TEMPLATE_MARKER = "__MEETING_TEMPLATE__";

export default function MeetingTemplatesPage() {
  const navigate = useNavigate();
  const templatesQuery = useCallTemplates();
  const createTemplate = useCreateCallTemplate();
  const updateTemplate = useUpdateCallTemplate();
  const deleteTemplate = useDeleteCallTemplate();
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const createForm = useForm({ defaultValues: { name: "" } });
  const editForm = useForm({ defaultValues: { name: "", is_active: true } });

  const rows = (templatesQuery.data ?? []).filter(
    (template) => template?.description === MEETING_TEMPLATE_MARKER,
  );

  const startEdit = (template) => {
    setEditing(template);
    editForm.reset({ name: template.name, is_active: template.is_active ?? true });
  };

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Meeting templates</h1>
          <p className="text-sm text-muted-foreground">Build versioned, fully dynamic fields for meeting forms.</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>New template</Button>
      </div>

      {templatesQuery.isError ? <PageError error={templatesQuery.error} onRetry={templatesQuery.refetch} /> : (
        <DataTable
          columns={[
            { key: "name", header: "Name" },
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

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>New meeting template</DialogTitle></DialogHeader>
          <form className="flex flex-col gap-4" onSubmit={createForm.handleSubmit(async (values) => {
            const template = await createTemplate.mutateAsync({ name: values.name, description: MEETING_TEMPLATE_MARKER });
            setCreateOpen(false);
            navigate(`/meeting-templates/${template.id}`);
          })}>
            <FormField id="meeting_template_name" label="Template name" required>
              <Input id="meeting_template_name" {...createForm.register("name", { required: true })} />
            </FormField>
            <DialogFooter><Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button><Button type="submit">Create & build fields</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(editing)} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent><DialogHeader><DialogTitle>Edit meeting template</DialogTitle></DialogHeader>
          <form className="flex flex-col gap-4" onSubmit={editForm.handleSubmit((values) => updateTemplate.mutateAsync({ id: editing.id, ...values }).then(() => setEditing(null)))}>
            <FormField id="edit_meeting_template_name" label="Name"><Input {...editForm.register("name")} /></FormField>
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
