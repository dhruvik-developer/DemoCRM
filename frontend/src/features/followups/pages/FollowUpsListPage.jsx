// Follow-ups list + create + status/delete row actions.
// Gotchas honored here: create gated on change_followup (G13), payload uses
// the `decription` typo key (G12), delete is HARD (warned in confirm).

import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import {
  FOLLOWUP_STATUSES,
  FOLLOWUP_TYPES,
  followUpStatusName,
  followUpTypeName,
} from "@/utils/followUpMasterData";
import TaskSelect from "@/features/tasks/components/TaskSelect";
import { useCreateFollowUp, useDeleteFollowUp, useFollowUps, useUpdateFollowUpStatus } from "../hooks";
import { followUpSchema } from "@/schemas/followUp.schema";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import FormField from "@/components/forms/FormField";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function CreateDialog({ open, onOpenChange }) {
  const createFollowUp = useCreateFollowUp();

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(followUpSchema),
    defaultValues: {
      task_id: "",
      followup_status_id: String(FOLLOWUP_STATUSES[0]?.id ?? ""),
      followup_type_id: String(FOLLOWUP_TYPES[0]?.id ?? ""),
      followup_date: "",
      decription: "",
    },
  });

  const taskId = useWatch({ control, name: "task_id" });
  const typeId = useWatch({ control, name: "followup_type_id" });
  const statusId = useWatch({ control, name: "followup_status_id" });

  const onSubmit = (values) =>
    createFollowUp
      .mutateAsync({
        // Payload keys match the backend exactly, including the G12 typo.
        task_id: values.task_id,
        followup_status: Number(values.followup_status_id),
        followup_type: Number(values.followup_type_id),
        followup_date: new Date(values.followup_date).toISOString(),
        decription: values.decription || undefined,
      })
      .then(() => onOpenChange(false));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Schedule follow-up</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <FormField id="task_id" label="Task" error={errors.task_id?.message}>
            <TaskSelect value={taskId} onChange={(value) => setValue("task_id", value)} />
          </FormField>

          <div className="grid gap-3 md:grid-cols-2">
            <FormField id="followup_type" label="Type" error={errors.followup_type_id?.message}>
              <Select value={typeId} onValueChange={(value) => setValue("followup_type_id", value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FOLLOWUP_TYPES.map((option) => (
                    <SelectItem key={option.id} value={String(option.id)}>
                      {option.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <FormField id="followup_status" label="Status">
              <Select value={statusId} onValueChange={(value) => setValue("followup_status_id", value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FOLLOWUP_STATUSES.map((option) => (
                    <SelectItem key={option.id} value={String(option.id)}>
                      {option.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
          </div>

          <FormField id="followup_date" label="Date & time" error={errors.followup_date?.message}
            help="Must be in the future."
          >
            <Input id="followup_date" type="datetime-local" {...register("followup_date")} />
          </FormField>

          {/* Backend field name is `decription` (G12) — label reads normally. */}
          <FormField id="decription" label="Description" error={errors.decription?.message}>
            <textarea
              id="decription"
              rows={3}
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm"
              {...register("decription")}
            />
          </FormField>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createFollowUp.isPending}>
              {createFollowUp.isPending ? "Scheduling…" : "Schedule"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function FollowUpsListPage() {
  const { resolved } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const page = Number(searchParams.get("page") ?? "1");
  const search = searchParams.get("search") ?? "";
  const updateParam = (key, value) => {
    setSearchParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (value) next.set(key, value);
        else next.delete(key);
        if (key !== "page") next.delete("page");
        return next;
      },
      { replace: true },
    );
  };

  const followUpsQuery = useFollowUps({ page, search: search || undefined });
  const updateStatus = useUpdateFollowUpStatus();
  const deleteFollowUp = useDeleteFollowUp();

  const [createOpen, setCreateOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);

  // G13: creating requires change_followup, NOT add_followup.
  const canCreate = hasPermission(resolved, "change_followup");
  const canChangeStatus = hasPermission(resolved, "change_followupstatus");
  const canDelete = hasPermission(resolved, "delete_followup");

  const rows = (followUpsQuery.data?.results ?? []).filter(Boolean);
  const count = followUpsQuery.data?.count ?? 0;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Follow-ups</h1>
        {canCreate ? (
          <Button onClick={() => setCreateOpen(true)}>Schedule follow-up</Button>
        ) : null}
      </div>

      <Input
        placeholder="Search…"
        className="w-64"
        defaultValue={search}
        onChange={(event) => updateParam("search", event.target.value.trim())}
      />

      {followUpsQuery.isError ? (
        <PageError error={followUpsQuery.error} onRetry={followUpsQuery.refetch} />
      ) : (
        <DataTable
          columns={[
            {
              key: "task_id",
              header: "Task",
              render: (row) =>
                row.task_id ? (
                  <Link to={`/tasks/${row.task_id}`} className="hover:underline">
                    #{row.task_id}
                  </Link>
                ) : (
                  "—"
                ),
            },
            {
              key: "followup_type",
              header: "Type",
              render: (row) => followUpTypeName(row.followup_type) ?? "—",
            },
            {
              key: "followup_status",
              header: "Status",
              render: (row) => (
                <Badge variant="outline">{followUpStatusName(row.followup_status)}</Badge>
              ),
            },
            {
              key: "followup_date",
              header: "When",
              sortable: true,
              render: (row) => new Date(row.followup_date).toLocaleString(),
            },
            {
              key: "actions",
              header: "",
              render: (row) => (
                <div className="flex items-center justify-end gap-2">
                  {canChangeStatus ? (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={updateStatus.isPending || row.followup_status === 2}
                      onClick={() =>
                        updateStatus.mutateAsync({ followUpId: row.followup_id, statusId: 2 })
                      }
                    >
                      Complete
                    </Button>
                  ) : null}
                  {canDelete ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive"
                      onClick={() => setPendingDelete(row)}
                    >
                      Delete
                    </Button>
                  ) : null}
                </div>
              ),
            },
          ]}
          rows={rows}
          getRowId={(row) => row?.followup_id ?? row?.id}
          isLoading={followUpsQuery.isLoading}
          emptyState={
            <EmptyState title="No follow-ups found" description={search ? "Try adjusting the search." : undefined} />
          }
          sortValue={searchParams.get("ordering") ?? ""}
          onSortChange={(value) => updateParam("ordering", value)}
          page={page}
          pageSize={10}
          count={count}
          onPageChange={(nextPage) => updateParam("page", String(nextPage))}
        />
      )}

      <CreateDialog open={createOpen} onOpenChange={setCreateOpen} />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title="Delete this follow-up?"
        description="This is a PERMANENT deletion — follow-ups cannot be recovered."
        confirmLabel="Delete permanently"
        destructive
        loading={deleteFollowUp.isPending}
        onConfirm={() => {
          if (!pendingDelete) return;
          deleteFollowUp.mutateAsync(pendingDelete.followup_id).then(() => setPendingDelete(null));
        }}
      />
    </div>
  );
}
