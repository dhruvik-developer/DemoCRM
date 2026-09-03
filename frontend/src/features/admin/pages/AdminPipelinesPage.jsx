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
import { useCallTemplates, useCreateStageActivity, useDeleteStageActivity, useStageActivitiesForStage, useUpdateStageActivity } from "@/features/callforms/hooks";
import { useRoles } from "@/features/admin/hooks";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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

function StageActivitiesAdmin({ stageId }) {
  const { data: activities } = useStageActivitiesForStage(stageId);
  const { data: templates } = useCallTemplates();
  const { data: roles } = useRoles();
  const createLink = useCreateStageActivity();
  const updateActivity = useUpdateStageActivity();
  const deleteActivity = useDeleteStageActivity();
  const [selected, setSelected] = useState("");
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [editRoles, setEditRoles] = useState([]);
  const [editEditable, setEditEditable] = useState([]);
  const [editFormType, setEditFormType] = useState("CALL");
  const [editFollowup, setEditFollowup] = useState(true);
  const [editOffset, setEditOffset] = useState(1);

  const list = Array.isArray(activities) ? activities : [];
  const roleOptions = Array.isArray(roles) ? roles.map((r) => r.rolename ?? r.name).filter(Boolean) : ["Manager", "Employee", "Admin"];

  const openEdit = (activity) => {
    setEditing(activity);
    setEditRoles(Array.isArray(activity.allowed_roles) ? activity.allowed_roles : []);
    setEditEditable(Array.isArray(activity.editable_roles) ? activity.editable_roles : []);
    setEditFormType(activity.form_type ?? "CALL");
    setEditFollowup(activity.auto_create_followup ?? true);
    setEditOffset(activity.followup_offset_days ?? 1);
  };

  const toggleRole = (rolename) => {
    setEditRoles((prev) => (prev.includes(rolename) ? prev.filter((r) => r !== rolename) : [...prev, rolename]));
  };
  const toggleEditable = (rolename) => {
    setEditEditable((prev) => (prev.includes(rolename) ? prev.filter((r) => r !== rolename) : [...prev, rolename]));
  };

  const handleSave = async () => {
    if (!editing) return;
    await updateActivity.mutateAsync({
      id: editing.id,
      allowed_roles: editRoles,
      editable_roles: editEditable,
      form_type: editFormType,
      auto_create_followup: editFollowup,
      followup_offset_days: Number(editOffset) || 1,
    });
    setEditing(null);
  };

  return (
    <div className="flex flex-col gap-2">
      {list.length ? (
        <div className="flex flex-col gap-1.5">
          {list.map((activity) => (
            <div key={activity.id} className="flex flex-col gap-1 rounded border bg-muted/20 px-2.5 py-2 text-xs">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{activity.name}</span>
                {activity.is_primary ? <Badge variant="default" className="text-[10px]">Primary</Badge> : null}
                <Badge variant="outline" className="text-[10px]">{activity.form_type ?? "CALL"}</Badge>
                <span className="text-muted-foreground">→ {activity.call_template_name ?? activity.call_template ?? "— no template —"}</span>
                <Button size="sm" variant="ghost" className="ml-auto h-6 text-[11px]" onClick={() => openEdit(activity)}>Edit</Button>
                <Button size="sm" variant="ghost" className="h-6 text-[11px] text-destructive hover:text-destructive" onClick={() => setDeleting(activity)}>Delete</Button>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                <span>View:</span>
                {!activity.allowed_roles?.length ? (
                  <Badge variant="secondary" className="text-[10px]">All roles</Badge>
                ) : (
                  activity.allowed_roles.map((r) => <Badge key={r} variant="outline" className="text-[10px]">{r}</Badge>)
                )}
                <span className="ml-1">Edit:</span>
                {!activity.editable_roles?.length ? (
                  <Badge variant="secondary" className="text-[10px]">Same</Badge>
                ) : (
                  activity.editable_roles.map((r) => <Badge key={r} variant="outline" className="text-[10px]">{r}</Badge>)
                )}
                <span className="ml-2">Follow-up:</span>
                <Badge variant={activity.auto_create_followup ? "secondary" : "outline"} className="text-[10px]">
                  {activity.auto_create_followup ? "ON" : "OFF"}
                </Badge>
                <span>+{activity.followup_offset_days ?? 1}d</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground italic">No call forms linked to this stage.</p>
      )}

      <div className="flex items-center gap-2 text-xs">
        <span className="text-muted-foreground">Link form:</span>
        <Select value={selected} onValueChange={setSelected}>
          <SelectTrigger className="h-7 w-44"><SelectValue placeholder="Select template" /></SelectTrigger>
          <SelectContent>
            {(templates ?? []).map((t) => <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button size="sm" variant="outline" className="h-7" disabled={!selected || createLink.isPending} onClick={() => createLink.mutateAsync({ stage: stageId, name: `Activity ${templates.find((t)=>t.id===selected)?.name}`, call_template: selected, is_primary: list.length === 0, activity_type: "CALL" }).then(()=>setSelected(""))}>Link</Button>
      </div>

      <Dialog open={Boolean(editing)} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Edit activity — {editing?.name}</DialogTitle></DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="text-sm font-medium">Form type (tab)</span>
              <Select value={editFormType} onValueChange={setEditFormType}>
                <SelectTrigger className="h-8 w-40"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["CALL", "PROPOSAL", "OFFER", "CONTRACT", "CUSTOM"].map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <span className="text-sm font-medium">Allowed roles — view (empty = all)</span>
              <div className="flex flex-wrap gap-2">
                {roleOptions.map((rolename) => (
                  <label key={rolename} className="flex items-center gap-1.5 rounded border px-2 py-1 text-xs cursor-pointer has-[:checked]:bg-muted">
                    <input type="checkbox" checked={editRoles.includes(rolename)} onChange={() => toggleRole(rolename)} className="h-3.5 w-3.5" />
                    {rolename}
                  </label>
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <span className="text-sm font-medium">Editable roles — submit (empty = same as view)</span>
              <div className="flex flex-wrap gap-2">
                {roleOptions.map((rolename) => (
                  <label key={rolename} className="flex items-center gap-1.5 rounded border px-2 py-1 text-xs cursor-pointer has-[:checked]:bg-muted">
                    <input type="checkbox" checked={editEditable.includes(rolename)} onChange={() => toggleEditable(rolename)} className="h-3.5 w-3.5" />
                    {rolename}
                  </label>
                ))}
              </div>
            </div>

            <label className="flex items-center gap-2 text-sm font-medium">
              <input type="checkbox" checked={editFollowup} onChange={(e) => setEditFollowup(e.target.checked)} className="h-4 w-4" />
              Auto-create follow-up (toggle)
            </label>

            <FormField id="followup_offset" label="Follow-up offset days (number)">
              <Input id="followup_offset" type="number" min="0" max="30" value={editOffset} onChange={(e) => setEditOffset(e.target.value)} disabled={!editFollowup} />
            </FormField>
            <p className="text-xs text-muted-foreground">PATCH /callforms/stage-activities/{`{id}`}/ — saved via updateStageActivity.</p>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
            <Button type="button" disabled={updateActivity.isPending} onClick={handleSave}>{updateActivity.isPending ? "Saving…" : "Save (PATCH)"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title={`Delete activity "${deleting?.name}"?`}
        description="This will remove the form link from the stage. Leads will no longer see this form."
        confirmLabel="Delete"
        destructive
        loading={deleteActivity.isPending}
        onConfirm={() => {
          if (!deleting) return;
          deleteActivity.mutateAsync(deleting.id).then(() => setDeleting(null));
        }}
      />
    </div>
  );
}

function PipelineStagesList({ pipelineId }) {
  const stagesQuery = usePipelineStages(pipelineId);
  const createStage = useCreatePipelineStage();
  const deleteStage = useDeletePipelineStage();

  const [addOpen, setAddOpen] = useState(false);
  const [deletingStage, setDeletingStage] = useState(null);

  const stageForm = useForm({
    defaultValues: { name: "", display_order: 1, description: "", requires_quotation: false, quotation_approval_required: false },
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
              className="flex flex-col gap-2 rounded border bg-background px-3 py-2 text-sm shadow-sm"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Badge variant="secondary" className="text-xs">
                    Stage {st.display_order ?? idx + 1}
                  </Badge>
                  <span className="font-medium">{st.name}</span>
                  {st.requires_quotation ? <Badge className="bg-amber-50 text-amber-700 border-amber-200 text-[10px]">Quotation</Badge> : null}
                  {st.quotation_approval_required ? <Badge variant="outline" className="text-[10px]">Approval</Badge> : null}
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
              <StageActivitiesAdmin stageId={st.id} />
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
                  requires_quotation: Boolean(values.requires_quotation),
                  quotation_approval_required: Boolean(values.quotation_approval_required),
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
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...stageForm.register("requires_quotation")} /> Requires quotation</label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...stageForm.register("quotation_approval_required")} /> Approval required</label>
            </div>
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
