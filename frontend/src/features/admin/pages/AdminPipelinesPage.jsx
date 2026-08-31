// Admin Pipelines & Stages management page — Admin / Manager only.
// View, Create, Edit, and Delete Pipelines and Pipeline Stages.

import { useState } from "react";
import { useForm } from "react-hook-form";

import {
  useCreatePipeline,
  useCreatePipelineStage,
  useDeletePipeline,
  useDeletePipelineStage,
  usePipelines,
  usePipelineStages,
  useUpdatePipeline,
} from "@/features/crm/hooks";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import FormField from "@/components/forms/FormField";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

function PipelineStagesList({ pipelineId }) {
  const stagesQuery = usePipelineStages(pipelineId);
  const createStage = useCreatePipelineStage();
  const deleteStage = useDeletePipelineStage();

  const [addOpen, setAddOpen] = useState(false);
  const [deletingStage, setDeletingStage] = useState(null);

  const stageForm = useForm({
    defaultValues: { name: "", display_order: 1, description: "" },
  });

  if (stagesQuery.isLoading) return <p className="text-xs text-muted-foreground">Loading stages…</p>;

  const stages = stagesQuery.data ?? [];

  return (
    <div className="flex flex-col gap-3 pt-2">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Pipeline Stages ({stages.length})
        </h4>
        <Button size="sm" variant="outline" onClick={() => setAddOpen(true)}>
          + Add stage
        </Button>
      </div>

      {!stages.length ? (
        <p className="text-xs text-muted-foreground italic">No stages in this pipeline yet.</p>
      ) : (
        <div className="grid gap-2">
          {stages.map((st, idx) => (
            <div
              key={st.id}
              className="flex items-center justify-between rounded border bg-background px-3 py-2 text-sm shadow-sm"
            >
              <div className="flex items-center gap-3">
                <Badge variant="secondary" className="text-xs">
                  Stage {st.display_order ?? idx + 1}
                </Badge>
                <span className="font-medium">{st.name}</span>
                {st.description ? (
                  <span className="text-xs text-muted-foreground">({st.description})</span>
                ) : null}
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs text-destructive hover:text-destructive"
                onClick={() => setDeletingStage(st)}
              >
                Remove
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Add Stage Dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Pipeline Stage</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={stageForm.handleSubmit((values) =>
              createStage
                .mutateAsync({
                  pipeline: pipelineId,
                  name: values.name,
                  display_order: Number(values.display_order),
                  description: values.description || undefined,
                })
                .then(() => {
                  setAddOpen(false);
                  stageForm.reset();
                }),
            )}
            className="flex flex-col gap-3"
          >
            <FormField id="stage_name" label="Stage Name" required>
              <Input id="stage_name" placeholder="e.g. Lead Contacted, Proposal Sent" {...stageForm.register("name")} />
            </FormField>
            <FormField id="stage_order" label="Display Order" required>
              <Input id="stage_order" type="number" min="1" {...stageForm.register("display_order")} />
            </FormField>
            <FormField id="stage_desc" label="Description">
              <Input id="stage_desc" placeholder="Details about this stage" {...stageForm.register("description")} />
            </FormField>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAddOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createStage.isPending}>
                {createStage.isPending ? "Adding…" : "Add stage"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Stage Confirm */}
      <ConfirmDialog
        open={Boolean(deletingStage)}
        onOpenChange={(open) => !open && setDeletingStage(null)}
        title={`Delete stage "${deletingStage?.name}"?`}
        description="Leads in this stage will need to be transitioned."
        confirmLabel="Delete stage"
        destructive
        loading={deleteStage.isPending}
        onConfirm={() => {
          if (!deletingStage) return;
          deleteStage.mutateAsync(deletingStage.id).then(() => setDeletingStage(null));
        }}
      />
    </div>
  );
}

export default function AdminPipelinesPage() {
  const pipelinesQuery = usePipelines();
  const createPipeline = useCreatePipeline();
  const updatePipeline = useUpdatePipeline();
  const deletePipeline = useDeletePipeline();

  const [createOpen, setCreateOpen] = useState(false);
  const [editingPipeline, setEditingPipeline] = useState(null);
  const [deletingPipeline, setDeletingPipeline] = useState(null);

  const createForm = useForm({ defaultValues: { name: "", description: "" } });
  const editForm = useForm({ defaultValues: { name: "", description: "" } });

  if (pipelinesQuery.isLoading) return <PageLoader label="Loading pipelines…" />;
  if (pipelinesQuery.isError) {
    return <PageError error={pipelinesQuery.error} onRetry={pipelinesQuery.refetch} />;
  }

  const pipelines = pipelinesQuery.data ?? [];

  const handleEditClick = (pipeline) => {
    setEditingPipeline(pipeline);
    editForm.reset({
      name: pipeline.name,
      description: pipeline.description ?? "",
    });
  };

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">CRM Pipelines</h1>
          <p className="text-sm text-muted-foreground">
            Configure sales pipelines and stages for tracking lead progress.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>New pipeline</Button>
      </div>

      {!pipelines.length ? (
        <EmptyState title="No pipelines configured" description="Create the first sales pipeline." />
      ) : (
        <div className="flex flex-col gap-6">
          {pipelines.map((pipeline) => (
            <Card key={pipeline.id}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div>
                  <CardTitle className="text-lg">{pipeline.name}</CardTitle>
                  {pipeline.description ? (
                    <p className="text-xs text-muted-foreground mt-0.5">{pipeline.description}</p>
                  ) : null}
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => handleEditClick(pipeline)}>
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => setDeletingPipeline(pipeline)}
                  >
                    Delete
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <PipelineStagesList pipelineId={pipeline.id} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Pipeline Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New sales pipeline</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={createForm.handleSubmit((values) =>
              createPipeline.mutateAsync(values).then(() => {
                setCreateOpen(false);
                createForm.reset();
              }),
            )}
            className="flex flex-col gap-3"
          >
            <FormField id="pipe_name" label="Pipeline Name" required>
              <Input id="pipe_name" placeholder="e.g. B2B Direct Sales, Enterprise Pipeline" {...createForm.register("name")} />
            </FormField>
            <FormField id="pipe_desc" label="Description">
              <Input id="pipe_desc" placeholder="Workflow overview" {...createForm.register("description")} />
            </FormField>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createPipeline.isPending}>
                {createPipeline.isPending ? "Creating…" : "Create pipeline"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Pipeline Dialog */}
      <Dialog open={Boolean(editingPipeline)} onOpenChange={(open) => !open && setEditingPipeline(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit pipeline — {editingPipeline?.name}</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={editForm.handleSubmit((values) =>
              updatePipeline
                .mutateAsync({ id: editingPipeline.id, ...values })
                .then(() => setEditingPipeline(null)),
            )}
            className="flex flex-col gap-4"
          >
            <FormField id="edit_pipe_name" label="Pipeline Name">
              <Input id="edit_pipe_name" {...editForm.register("name")} />
            </FormField>
            <FormField id="edit_pipe_desc" label="Description">
              <Input id="edit_pipe_desc" {...editForm.register("description")} />
            </FormField>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditingPipeline(null)}>
                Cancel
              </Button>
              <Button type="submit" disabled={updatePipeline.isPending}>
                {updatePipeline.isPending ? "Saving…" : "Save changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Pipeline Dialog */}
      <ConfirmDialog
        open={Boolean(deletingPipeline)}
        onOpenChange={(open) => !open && setDeletingPipeline(null)}
        title={`Delete pipeline "${deletingPipeline?.name}"?`}
        description="This will remove the pipeline and all associated stages."
        confirmLabel="Delete pipeline"
        destructive
        loading={deletePipeline.isPending}
        onConfirm={() => {
          if (!deletingPipeline) return;
          deletePipeline.mutateAsync(deletingPipeline.id).then(() => setDeletingPipeline(null));
        }}
      />
    </div>
  );
}
