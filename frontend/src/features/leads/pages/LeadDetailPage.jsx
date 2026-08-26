// Lead detail: status badge + workflow action bar. Every action maps to a
// dedicated backend endpoint — status is NEVER directly editable (rule #10).
// Button visibility follows status + permissions (PERMISSION_CONTRACT.md).

import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { useMasterDataMaps, usePipelineStages } from "@/features/crm/hooks";
import {
  useAssignLead,
  useConvertLead,
  useLead,
  useMarkLeadLost,
  useProgressLead,
  useReengageLead,
} from "../hooks";
import ActivitiesCard from "@/features/activities/components/ActivitiesCard";
import {
  assignLeadSchema,
  convertLeadSchema,
  lostLeadSchema,
} from "@/schemas/lead.schema";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import StatusBadge from "@/components/common/StatusBadge";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";

function Field({ label, value }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="text-sm">{value ?? "—"}</span>
    </div>
  );
}

function AssignDialog({ lead, open, onOpenChange }) {
  const assignLead = useAssignLead(lead.id);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(assignLeadSchema) });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign lead</DialogTitle>
        </DialogHeader>
        {/* G6: no user-list endpoint yet, so v1 takes a user UUID directly. */}
        <form onSubmit={handleSubmit((values) => assignLead.mutateAsync(values.assigned_to).then(() => onOpenChange(false)))}>
          <FormField
            id="assigned_to"
            label="User UUID"
            error={errors.assigned_to?.message}
            help="A searchable user picker will replace this once the backend ships GET /users/."
          >
            <Input id="assigned_to" placeholder="00000000-0000-4000-8000-…" {...register("assigned_to")} />
          </FormField>
          <DialogFooter className="mt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={assignLead.isPending}>
              {assignLead.isPending ? "Assigning…" : "Assign"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ProgressDialog({ lead, open, onOpenChange }) {
  const progressLead = useProgressLead(lead.id);
  const stagesQuery = usePipelineStages(lead.pipeline);
  const [stageId, setStageId] = useState("");

  // Default: next stage after the current one.
  const defaultNext = useMemo(() => {
    const stages = stagesQuery.data ?? [];
    const index = stages.findIndex((stage) => stage.id === lead.current_stage);
    return stages[index + 1]?.id ?? "";
  }, [stagesQuery.data, lead.current_stage]);

  const selected = stageId || defaultNext;
  const currentOrder = (stagesQuery.data ?? []).find(
    (stage) => stage.id === lead.current_stage,
  )?.display_order;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Move to next stage</DialogTitle>
        </DialogHeader>
        <Select value={selected} onValueChange={setStageId}>
          <SelectTrigger>
            <SelectValue placeholder="Select stage" />
          </SelectTrigger>
          <SelectContent>
            {(stagesQuery.data ?? [])
              .filter((stage) => stage.is_active && stage.display_order > currentOrder)
              .map((stage) => (
                <SelectItem key={stage.id} value={stage.id}>
                  {stage.display_order}. {stage.name}
                  {stage.requires_quotation ? " (requires quotation)" : ""}
                </SelectItem>
              ))}
          </SelectContent>
        </Select>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!selected || progressLead.isPending}
            onClick={() => progressLead.mutateAsync(selected).then(() => onOpenChange(false))}
          >
            {progressLead.isPending ? "Moving…" : "Move"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function LostDialog({ lead, open, onOpenChange }) {
  const markLost = useMarkLeadLost(lead.id);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(lostLeadSchema) });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Mark lead lost</DialogTitle>
        </DialogHeader>
        {/* Backend rule #11: LOST requires a reason; it is stored with a timestamp. */}
        <form onSubmit={handleSubmit((values) => markLost.mutateAsync(values.lost_reason).then(() => onOpenChange(false)))}>
          <FormField id="lost_reason" label="Reason (required)" error={errors.lost_reason?.message}>
            <textarea
              id="lost_reason"
              rows={3}
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm"
              {...register("lost_reason")}
            />
          </FormField>
          <DialogFooter className="mt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" disabled={markLost.isPending}>
              {markLost.isPending ? "Saving…" : "Mark lost"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ConvertDialog({ lead, open, onOpenChange }) {
  const convertLead = useConvertLead(lead.id);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(convertLeadSchema),
    defaultValues: {
      name: lead.name ?? "",
      email: lead.email ?? "",
      phone: lead.phone ?? "",
      company_name: lead.company_name ?? "",
      gst_number: "",
    },
  });

  const onSubmit = (values) =>
    convertLead
      .mutateAsync({
        name: values.name,
        email: values.email,
        phone: values.phone,
        company_name: values.company_name || undefined,
        gst_number: values.gst_number || undefined,
      })
      .then(() => onOpenChange(false));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Convert lead to customer</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          An exact email+phone match returns the existing customer instead of
          creating a duplicate. A GST number links the customer to an existing
          account when one matches.
        </p>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3">
          <FormField id="convert_name" label="Name" error={errors.name?.message}>
            <Input id="convert_name" {...register("name")} />
          </FormField>
          <div className="grid gap-3 md:grid-cols-2">
            <FormField id="convert_email" label="Email" error={errors.email?.message}>
              <Input id="convert_email" type="email" {...register("email")} />
            </FormField>
            <FormField id="convert_phone" label="Phone" error={errors.phone?.message}>
              <Input id="convert_phone" {...register("phone")} />
            </FormField>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <FormField id="convert_company" label="Company" error={errors.company_name?.message}>
              <Input id="convert_company" {...register("company_name")} />
            </FormField>
            <FormField id="convert_gst" label="GST number" error={errors.gst_number?.message}>
              <Input id="convert_gst" {...register("gst_number")} />
            </FormField>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={convertLead.isPending}>
              {convertLead.isPending ? "Converting…" : "Convert"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function LeadDetailPage() {
  const { leadId } = useParams();
  const { resolved } = useAuth();
  const leadQuery = useLead(leadId);
  const masterData = useMasterDataMaps();

  const [dialog, setDialog] = useState(null); // 'assign' | 'progress' | 'lost' | 'convert'
  const [reengageOpen, setReengageOpen] = useState(false);
  const reengageLead = useReengageLead(leadId);

  if (leadQuery.isLoading) return <PageLoader label="Loading lead…" />;
  if (leadQuery.isError) {
    return <PageError error={leadQuery.error} onRetry={leadQuery.refetch} />;
  }

  const lead = leadQuery.data;
  const status = lead.status;
  const can = (codename) => hasPermission(resolved, codename);
  const isActive = status === "ACTIVE";
  const isLost = status === "LOST";

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">{lead.name}</h1>
          <StatusBadge status={status} />
          {isLost && lead.lost_reason ? (
            <Badge variant="outline">{lead.lost_reason}</Badge>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {isActive && can("assign_lead") ? (
            <Button variant="outline" size="sm" onClick={() => setDialog("assign")}>
              Assign
            </Button>
          ) : null}
          {isActive && can("progress_lead") ? (
            <Button size="sm" onClick={() => setDialog("progress")}>
              Progress
            </Button>
          ) : null}
          {isActive && can("convert_lead") ? (
            <Button size="sm" onClick={() => setDialog("convert")}>
              Convert
            </Button>
          ) : null}
          {isActive && can("mark_lead_lost") ? (
            <Button variant="destructive" size="sm" onClick={() => setDialog("lost")}>
              Mark lost
            </Button>
          ) : null}
          {isLost && can("reengage_lead") ? (
            <Button variant="outline" size="sm" onClick={() => setReengageOpen(true)}>
              Re-engage
            </Button>
          ) : null}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <Field label="Email" value={lead.email} />
          <Field label="Phone" value={lead.phone} />
          <Field label="Company" value={lead.company_name} />
          <Field label="Pipeline" value={masterData.pipelineName(lead.pipeline)} />
          <Field
            label="Current stage"
            value={masterData.stageName(lead.current_stage)}
          />
          <Field label="Source" value={masterData.sourceName(lead.source)} />
          <Field label="Total value" value={lead.total_value} />
          <Field label="Paid amount" value={lead.paid_amount} />
          <Field label="Due amount" value={lead.due_amount} />
          <Field
            label="Assigned to"
            // No user-list endpoint (G6) — show a short UUID reference.
            value={
              lead.assigned_to ? `${String(lead.assigned_to).slice(0, 8)}…` : null
            }
          />
          <Field label="Created" value={lead.created_at ? new Date(lead.created_at).toLocaleString() : null} />
        </CardContent>
      </Card>

      <Separator />

      <ActivitiesCard leadId={lead.id} blocked={status === "CONVERTED"} />

      <p className="text-sm text-muted-foreground">
        Quotations and timeline tabs for this lead arrive with Phases 12 and 14.
      </p>

      <AssignDialog lead={lead} open={dialog === "assign"} onOpenChange={(open) => !open && setDialog(null)} />
      <ProgressDialog lead={lead} open={dialog === "progress"} onOpenChange={(open) => !open && setDialog(null)} />
      <LostDialog lead={lead} open={dialog === "lost"} onOpenChange={(open) => !open && setDialog(null)} />
      <ConvertDialog lead={lead} open={dialog === "convert"} onOpenChange={(open) => !open && setDialog(null)} />

      <ConfirmDialog
        open={reengageOpen}
        onOpenChange={setReengageOpen}
        title="Re-engage this lead?"
        description="The lead will return to ACTIVE and its lost reason/timestamp will be cleared."
        confirmLabel="Re-engage"
        loading={reengageLead.isPending}
        onConfirm={() => reengageLead.mutateAsync().then(() => setReengageOpen(false))}
      />

      <Link to="/leads" className="text-sm text-muted-foreground hover:underline">
        ← Back to leads
      </Link>
    </div>
  );
}
