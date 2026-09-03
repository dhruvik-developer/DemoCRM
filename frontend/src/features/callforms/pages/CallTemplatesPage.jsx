import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import {
  useCallTemplates,
  useCreateCallTemplate,
  useDeleteCallTemplate,
  useUpdateCallTemplate,
} from "../hooks";
import { callTemplateSchema } from "@/schemas/callform.schema";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import FormField from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export default function CallTemplatesPage() {
  const templatesQuery = useCallTemplates();
  const createTemplate = useCreateCallTemplate();
  const updateTemplate = useUpdateCallTemplate();
  const deleteTemplate = useDeleteCallTemplate();

  const [createOpen, setCreateOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [deletingTemplate, setDeletingTemplate] = useState(null);

  const createForm = useForm({ resolver: zodResolver(callTemplateSchema) });
  const editForm = useForm({
    defaultValues: { name: "", is_active: true },
  });

  const rows = (templatesQuery.data ?? []).filter(
    (template) => template?.description !== "__MEETING_TEMPLATE__",
  );

  const handleEditClick = (template) => {
    setEditingTemplate(template);
    editForm.reset({
      name: template.name,
      is_active: template.is_active ?? true,
    });
  };

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Call form templates</h1>
          <p className="text-sm text-muted-foreground">
            Manage call form templates, template versions, and form field layouts.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>New template</Button>
      </div>

      {templatesQuery.isError ? (
        <PageError error={templatesQuery.error} onRetry={templatesQuery.refetch} />
      ) : (
        <DataTable
          columns={[
            {
              key: "name",
              header: "Name",
              render: (template) => (
                <Link to={`/callforms/templates/${template.id}`} className="font-medium hover:underline">
                  {template.name}
                </Link>
              ),
            },
            {
              key: "is_active",
              header: "Active",
              render: (template) => (template.is_active ? "Yes" : "No"),
            },
            {
              key: "actions",
              header: "Actions",
              render: (template) => (
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => handleEditClick(template)}>
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => setDeletingTemplate(template)}
                  >
                    Delete
                  </Button>
                </div>
              ),
            },
          ]}
          rows={rows}
          getRowId={(row) => row.id}
          isLoading={templatesQuery.isLoading}
          emptyState={<EmptyState title="No templates yet" description="Create the first call form template." />}
          page={1}
          pageSize={Math.max(rows.length, 1)}
          count={rows.length}
        />
      )}

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New call form template</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={createForm.handleSubmit((values) =>
              createTemplate.mutateAsync({ ...values, initial_fields: [] }).then(() => { setCreateOpen(false); createForm.reset(); }),
            )}
            className="flex flex-col gap-3"
          >
            <FormField id="template_name" label="Name" error={createForm.formState.errors.name?.message}>
              <Input id="template_name" {...createForm.register("name")} />
            </FormField>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createTemplate.isPending}>
                {createTemplate.isPending ? "Creating…" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={Boolean(editingTemplate)} onOpenChange={(open) => !open && setEditingTemplate(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit template — {editingTemplate?.name}</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={editForm.handleSubmit((values) =>
              updateTemplate
                .mutateAsync({ id: editingTemplate.id, ...values })
                .then(() => setEditingTemplate(null)),
            )}
            className="flex flex-col gap-4"
          >
            <FormField id="edit_name" label="Template Name">
              <Input id="edit_name" {...editForm.register("name")} />
            </FormField>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                className="h-4 w-4"
                {...editForm.register("is_active")}
              />
              Active Template
            </label>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditingTemplate(null)}>
                Cancel
              </Button>
              <Button type="submit" disabled={updateTemplate.isPending}>
                {updateTemplate.isPending ? "Saving…" : "Save changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={Boolean(deletingTemplate)}
        onOpenChange={(open) => !open && setDeletingTemplate(null)}
        title={`Delete template "${deletingTemplate?.name}"?`}
        description="This will remove the template and its versions."
        confirmLabel="Delete"
        destructive
        loading={deleteTemplate.isPending}
        onConfirm={() => {
          if (!deletingTemplate) return;
          deleteTemplate.mutateAsync(deletingTemplate.id).then(() => setDeletingTemplate(null));
        }}
      />
    </div>
  );
}
