// Admin Lead Sources management page — Admin / Manager only.
// View, Create, Edit name/active status, and Delete lead sources.

import { useState } from "react";
import { useForm } from "react-hook-form";

import {
  useCreateLeadSource,
  useDeleteLeadSource,
  useLeadSources,
  useUpdateLeadSource,
} from "@/features/crm/hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
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

export default function AdminLeadSourcesPage() {
  const sourcesQuery = useLeadSources();
  const createSource = useCreateLeadSource();
  const updateSource = useUpdateLeadSource();
  const deleteSource = useDeleteLeadSource();

  const [createOpen, setCreateOpen] = useState(false);
  const [editingSource, setEditingSource] = useState(null);
  const [deletingSource, setDeletingSource] = useState(null);

  const createForm = useForm({ defaultValues: { name: "", description: "" } });
  const editForm = useForm({ defaultValues: { name: "", description: "", is_active: true } });

  if (sourcesQuery.isLoading) return <PageLoader label="Loading lead sources…" />;
  if (sourcesQuery.isError) {
    return <PageError error={sourcesQuery.error} onRetry={sourcesQuery.refetch} />;
  }

  const sources = sourcesQuery.data ?? [];

  const handleEditClick = (source) => {
    setEditingSource(source);
    editForm.reset({
      name: source.name,
      description: source.description ?? "",
      is_active: source.is_active ?? true,
    });
  };

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Lead Sources</h1>
          <p className="text-sm text-muted-foreground">
            Manage lead sources available across lead creation and attachment workflows.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>New lead source</Button>
      </div>

      <DataTable
        columns={[
          {
            key: "name",
            header: "Source Name",
            render: (source) => <span className="font-semibold text-foreground">{source.name}</span>,
          },
          {
            key: "description",
            header: "Description",
            render: (source) => (
              <span className="text-sm text-muted-foreground">{source.description || "—"}</span>
            ),
          },
          {
            key: "is_active",
            header: "Status",
            render: (source) =>
              source.is_active ? (
                <Badge variant="secondary">Active</Badge>
              ) : (
                <Badge variant="outline" className="text-muted-foreground">Inactive</Badge>
              ),
          },
          {
            key: "actions",
            header: "Actions",
            render: (source) => (
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => handleEditClick(source)}>
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setDeletingSource(source)}
                >
                  Delete
                </Button>
              </div>
            ),
          },
        ]}
        rows={sources}
        getRowId={(row) => row.id}
        isLoading={sourcesQuery.isLoading}
        emptyState={<EmptyState title="No lead sources yet" description="Create your first lead source." />}
        page={1}
        pageSize={Math.max(sources.length, 1)}
        count={sources.length}
      />

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New lead source</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={createForm.handleSubmit((values) =>
              createSource.mutateAsync(values).then(() => {
                setCreateOpen(false);
                createForm.reset();
              }),
            )}
            className="flex flex-col gap-3"
          >
            <FormField id="source_name" label="Source Name" required>
              <Input id="source_name" placeholder="e.g. Website Inquiry, Referral, Campaign" {...createForm.register("name")} />
            </FormField>
            <FormField id="source_desc" label="Description">
              <Input id="source_desc" placeholder="Details about this lead channel" {...createForm.register("description")} />
            </FormField>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createSource.isPending}>
                {createSource.isPending ? "Creating…" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={Boolean(editingSource)} onOpenChange={(open) => !open && setEditingSource(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit lead source — {editingSource?.name}</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={editForm.handleSubmit((values) =>
              updateSource
                .mutateAsync({ id: editingSource.id, ...values })
                .then(() => setEditingSource(null)),
            )}
            className="flex flex-col gap-4"
          >
            <FormField id="edit_source_name" label="Source Name">
              <Input id="edit_source_name" {...editForm.register("name")} />
            </FormField>
            <FormField id="edit_source_desc" label="Description">
              <Input id="edit_source_desc" {...editForm.register("description")} />
            </FormField>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" className="h-4 w-4" {...editForm.register("is_active")} />
              Active Source
            </label>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditingSource(null)}>
                Cancel
              </Button>
              <Button type="submit" disabled={updateSource.isPending}>
                {updateSource.isPending ? "Saving…" : "Save changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <ConfirmDialog
        open={Boolean(deletingSource)}
        onOpenChange={(open) => !open && setDeletingSource(null)}
        title={`Delete lead source "${deletingSource?.name}"?`}
        description="Leads attached to this source will retain their source record."
        confirmLabel="Delete"
        destructive
        loading={deleteSource.isPending}
        onConfirm={() => {
          if (!deletingSource) return;
          deleteSource.mutateAsync(deletingSource.id).then(() => setDeletingSource(null));
        }}
      />
    </div>
  );
}
