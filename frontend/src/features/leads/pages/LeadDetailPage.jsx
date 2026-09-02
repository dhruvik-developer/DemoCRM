// Lead detail → Sales Workspace (CRM_FRONTEND_AGENT_MASTER_PROMPT.md §6)
// Status is never directly editable; all actions via dedicated endpoints.
// Uses reusable workflow engine + Stitch DESIGN.md styling (rounded-xl, #2563EB).

import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useAuth } from "@/hooks/useAuth";
import { useWorkflowCapabilities } from "@/hooks/useWorkflowCapabilities";
import { useMasterDataMaps, usePipelineStages } from "@/features/crm/hooks";
import {
  useAssignLead,
  useConvertLead,
  useLead,
  useMarkLeadLost,
  useProgressLead,
  useReengageLead,
} from "../hooks";
import { useLeadPrimaryForm, useSubmitForm } from "@/features/callforms/hooks";
import DynamicFormFields from "@/features/callforms/components/DynamicFormFields";
import ActivitiesCard from "@/features/activities/components/ActivitiesCard";
import { convertLeadSchema, lostLeadSchema } from "@/schemas/lead.schema";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import StatusBadge from "@/components/common/StatusBadge";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import FormField from "@/components/forms/FormField";
import PipelineStepper from "@/components/workflow/PipelineStepper";
import LeadSummary, { TaskSummary } from "@/components/sales/LeadSummary";
import DynamicStageForm from "@/components/sales/DynamicStageForm";
import FormResponseHistory from "@/components/sales/FormResponseHistory";
import QuotationPanel from "@/components/sales/QuotationPanel";
import SalesTimeline from "@/components/sales/SalesTimeline";
import CallAttemptPanel from "@/components/sales/CallAttemptPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { useUsers } from "@/features/admin/hooks";
import { useQuotations } from "@/features/quotations/hooks";
import { useTasks } from "@/features/tasks/hooks";

function Field({ label, value }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="text-sm">{value ?? "—"}</span>
    </div>
  );
}

function AssignDialog({ lead, open, onOpenChange }) {
  const assignLead = useAssignLead(lead.id);
  const usersQuery = useUsers();
  const [selectedUserId, setSelectedUserId] = useState(lead.assigned_to?.user_id ?? lead.assigned_to ?? "");
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign lead</DialogTitle>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!selectedUserId) return;
            assignLead.mutateAsync(selectedUserId).then(() => onOpenChange(false));
          }}
        >
          <FormField id="assigned_to" label="Select Employee" help="Select an employee to assign this lead to.">
            <Select value={selectedUserId} onValueChange={setSelectedUserId}>
              <SelectTrigger>
                <SelectValue placeholder="Select Employee" />
              </SelectTrigger>
              <SelectContent>
                {(usersQuery.data ?? []).map((user) => (
                  <SelectItem key={user.user_id} value={user.user_id}>
                    {user.full_name || user.username} {user.role ? `(${user.role})` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
          <DialogFooter className="mt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!selectedUserId || assignLead.isPending}>
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
  const primaryFormQuery = useLeadPrimaryForm(lead.id);
  const submitForm = useSubmitForm();
  const [stageId, setStageId] = useState("");
  const [formValues, setFormValues] = useState({});
  const [fieldErrors, setFieldErrors] = useState({});

  const defaultNext = useMemo(() => {
    const stages = stagesQuery.data ?? [];
    const index = stages.findIndex((stage) => stage.id === lead.current_stage);
    return stages[index + 1]?.id ?? "";
  }, [stagesQuery.data, lead.current_stage]);

  const selected = stageId || defaultNext;
  const currentOrder = (stagesQuery.data ?? []).find((stage) => stage.id === lead.current_stage)?.display_order;
  const formData = primaryFormQuery.data;
  const hasFields = Boolean(formData?.fields?.length);

  const handleProgress = async () => {
    setFieldErrors({});
    if (hasFields) {
      const errors = {};
      for (const field of formData.fields) if (field.is_required && !formValues[field.field_key]) errors[field.field_key] = `${field.label} is required.`;
      if (Object.keys(errors).length) { setFieldErrors(errors); return; }
      try {
        await submitForm.mutateAsync({ lead_id: lead.id, template_version_id: formData.template_version_id || formData.id, data: formValues });
      } catch { return; }
    }
    await progressLead.mutateAsync(selected);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={hasFields ? "max-h-[85vh] overflow-y-auto max-w-2xl" : ""}>
        <DialogHeader>
          <DialogTitle>Move to next stage</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <FormField id="progress_stage" label="Next Stage">
            <Select value={selected} onValueChange={setStageId}>
              <SelectTrigger id="progress_stage">
                <SelectValue placeholder="Select stage" />
              </SelectTrigger>
              <SelectContent>
                {(stagesQuery.data ?? [])
                  .filter((stage) => (stage.is_active ?? true) && stage.display_order > currentOrder)
                  .map((stage) => (
                    <SelectItem key={stage.id} value={stage.id}>
                      {stage.display_order}. {stage.name}
                      {stage.requires_quotation ? " (requires quotation)" : ""}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </FormField>
          {hasFields ? (
            <div className="rounded-lg border bg-muted/30 p-3.5 flex flex-col gap-3">
              <h4 className="text-sm font-semibold text-foreground">Current Stage Form Answers ({formData.template_name || "Form"})</h4>
              <DynamicFormFields fields={formData.fields} values={formValues} errors={fieldErrors} onChange={setFormValues} stepView={true} />
            </div>
          ) : null}
        </div>
        <DialogFooter className="pt-3">
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button disabled={!selected || progressLead.isPending || submitForm.isPending} onClick={handleProgress}>
            {progressLead.isPending || submitForm.isPending ? "Saving & Moving…" : "Submit Form & Move Stage"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function LostDialog({ lead, open, onOpenChange }) {
  const markLost = useMarkLeadLost(lead.id);
  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(lostLeadSchema) });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Mark lead lost</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit((values) => markLost.mutateAsync(values.lost_reason).then(() => onOpenChange(false)))}>
          <FormField id="lost_reason" label="Reason (required)" error={errors.lost_reason?.message}>
            <textarea id="lost_reason" rows={3} className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm" {...register("lost_reason")} />
          </FormField>
          <DialogFooter className="mt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" variant="destructive" disabled={markLost.isPending}>{markLost.isPending ? "Saving…" : "Mark lost"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ConvertDialog({ lead, open, onOpenChange }) {
  const navigate = useNavigate();
  const convertLead = useConvertLead(lead.id);
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(convertLeadSchema),
    defaultValues: { name: lead.name ?? "", email: lead.email ?? "", phone: lead.phone ?? "", company_name: lead.company_name ?? "", gst_number: "" },
  });
  const onSubmit = (values) => convertLead.mutateAsync({ name: values.name, email: values.email, phone: values.phone, company_name: values.company_name || undefined, gst_number: values.gst_number || undefined }).then((customer) => {
    onOpenChange(false);
    if (customer?.id) navigate(`/customers/${customer.id}`);
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader><DialogTitle>Convert lead to customer</DialogTitle></DialogHeader>
        <p className="text-sm text-muted-foreground">An exact email+phone match returns the existing customer instead of creating a duplicate. A GST number links the customer to an existing account when one matches.</p>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3">
          <FormField id="convert_name" label="Name" error={errors.name?.message}><Input id="convert_name" {...register("name")} /></FormField>
          <div className="grid gap-3 md:grid-cols-2">
            <FormField id="convert_email" label="Email" error={errors.email?.message}><Input id="convert_email" type="email" {...register("email")} /></FormField>
            <FormField id="convert_phone" label="Phone" error={errors.phone?.message}><Input id="convert_phone" {...register("phone")} /></FormField>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <FormField id="convert_company" label="Company" error={errors.company_name?.message}><Input id="convert_company" {...register("company_name")} /></FormField>
            <FormField id="convert_gst" label="GST number" error={errors.gst_number?.message}><Input id="convert_gst" {...register("gst_number")} /></FormField>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={convertLead.isPending}>{convertLead.isPending ? "Converting…" : "Convert"}</Button>
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
  const usersQuery = useUsers();
  const masterData = useMasterDataMaps();
  const stagesQuery = usePipelineStages(leadQuery.data?.pipeline);
  const primaryFormQuery = useLeadPrimaryForm(leadId);
  const quotationsQuery = useQuotations({ lead: leadId });
  const tasksQuery = useTasks({ lead: leadId });

  const [dialog, setDialog] = useState(null);
  const [reengageOpen, setReengageOpen] = useState(false);
  const reengageLead = useReengageLead(leadId);

  const lead = leadQuery.data;
  const stages = stagesQuery.data ?? [];
  const currentStage = lead ? (stages.find((s) => s.id === lead.current_stage) ?? null) : null;
  const currentForm = primaryFormQuery.data ?? null;
  const latestQuotation = (quotationsQuery.data?.results ?? quotationsQuery.data ?? [])[0] ?? null;
  const currentTask = (tasksQuery.data?.results ?? tasksQuery.data ?? [])[0] ?? null;

  const caps = useWorkflowCapabilities({ lead, stages, currentStage, currentForm, permissions: resolved, quotation: latestQuotation, task: currentTask });

  if (leadQuery.isLoading) return <PageLoader label="Loading lead…" />;
  if (leadQuery.isError) return <PageError error={leadQuery.error} onRetry={leadQuery.refetch} />;

  const assignedLabel = (() => {
    if (!lead.assigned_to) return null;
    if (typeof lead.assigned_to === "object") return lead.assigned_to.full_name || lead.assigned_to.username || lead.assigned_to.email;
    const found = (usersQuery?.data ?? []).find((u) => String(u.user_id) === String(lead.assigned_to));
    return found?.full_name || found?.username || `${String(lead.assigned_to).slice(0, 8)}…`;
  })();

  return (
    <div className="mx-auto flex w-full max-w-[1480px] flex-col gap-5 p-6 lg:px-7 lg:py-6">
      {/* Hero Card — single composite like sample hero-card:258 */}
      <Card className="rounded-[14px] border-[#E2E8F0] shadow-[0_1px_2px_rgba(0,0,0,0.05)] overflow-hidden">
        <CardContent className="p-0">
          <div className="p-[22px_26px]">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 text-[12px] font-semibold text-muted-foreground">
                  <span>{masterData.pipelineName(lead.pipeline) ? `Pipeline: ${masterData.pipelineName(lead.pipeline)}` : "Pipeline"}</span>
                  <span>•</span>
                  <StatusBadge status={lead.status} />
                  {masterData.stageName(lead.current_stage) ? <Badge className="bg-[#EEF2FF] text-[#4F46E5] border-[#C7D2FE] text-[11px] font-bold">{masterData.stageName(lead.current_stage)}</Badge> : null}
                </div>
                <h1 className="mt-1 truncate text-[24px] font-extrabold tracking-[-0.03em] text-[#0F172A]">{lead.name}</h1>
                <div className="mt-1.5 flex flex-wrap items-center gap-3.5 text-[13px] text-muted-foreground">
                  <span className="inline-flex items-center gap-1.5">👤 {lead.company_name ?? "—"}</span>
                  <span className="inline-flex items-center gap-1.5">✉️ {lead.email ?? "—"}</span>
                  <span className="inline-flex items-center gap-1.5">📞 {lead.phone ?? "—"}</span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3 text-sm md:grid-cols-4 lg:hidden">
                  <Field label="Pipeline" value={masterData.pipelineName(lead.pipeline)} />
                  <Field label="Current stage" value={masterData.stageName(lead.current_stage)} />
                  <Field label="Source" value={masterData.sourceName(lead.source)} />
                  <Field label="Assigned" value={assignedLabel ?? "—"} />
                </div>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2 lg:justify-end">
                {caps.canMarkLost ? <Button variant="ghost" size="sm" className="text-[#DC2626] hover:bg-[#FEF2F2] font-semibold" onClick={() => setDialog("lost")}>Mark Lost</Button> : null}
                {caps.canProgress ? <Button size="sm" className="bg-[#2563EB] hover:bg-[#1D4ED8] font-semibold" onClick={() => setDialog("progress")}>Submit & Move →</Button> : caps.canConvert ? <Button size="sm" className="bg-[#2563EB] hover:bg-[#1D4ED8] font-semibold" onClick={() => setDialog("convert")}>Convert 🚀</Button> : null}
                {caps.canAssign ? <Button variant="outline" size="sm" className="font-semibold" onClick={() => setDialog("assign")}>Assign</Button> : null}
              </div>
            </div>
          </div>
          <div className="border-t border-[#F1F5F9] px-6 py-2">
            <PipelineStepper stages={stages} currentStageId={lead.current_stage} stageEnteredAt={lead.updated_at ?? lead.created_at} />
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center gap-2">
        {caps.canReengage ? <Button variant="outline" size="sm" onClick={() => setReengageOpen(true)}>Re-engage</Button> : null}
        {lead.status === "LOST" && lead.lost_reason ? <Badge variant="outline" className="max-w-[260px] truncate">{lead.lost_reason}</Badge> : null}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <LeadSummary lead={lead} sourceName={masterData.sourceName(lead.source)} pipelineName={masterData.pipelineName(lead.pipeline)} assignedLabel={assignedLabel} />
        <TaskSummary task={currentTask} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.85fr_0.95fr]">
        <div className="flex flex-col gap-5">
          <CallAttemptPanel leadId={lead.id} stageId={lead.current_stage} templateVersionId={currentForm?.template_version_id ?? currentForm?.id} />
          <DynamicStageForm lead={lead} />
          <FormResponseHistory leadId={lead.id} />
          <SalesTimeline leadId={lead.id} />
        </div>
        <div className="flex flex-col gap-5">
          <QuotationPanel leadId={lead.id} requiresQuotation={caps.requiresQuotation} />
          <Card className="rounded-[14px] border-[#E2E8F0] shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
            <CardHeader className="pb-3"><CardTitle className="text-sm font-bold">Quick Operations</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-2">
              <Button variant="outline" className="justify-start font-medium" onClick={() => setDialog("assign")}>📅 Schedule Review Meeting</Button>
              <Button variant="outline" className="justify-start font-medium" asChild><Link to={`/tasks/new?lead=${lead.id}`}>🔔 Set Follow-up Reminder</Link></Button>
              <Button variant="outline" className="justify-start font-medium" asChild><Link to={`/quotations/new?lead=${lead.id}`}>💬 Send Quotation</Link></Button>
            </CardContent>
          </Card>
          <ActivitiesCard leadId={lead.id} blocked={lead.status === "CONVERTED"} />
        </div>
      </div>

      <Card className="rounded-[14px] border-[#E2E8F0]">
        <CardHeader><CardTitle className="text-sm font-bold">Details</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <Field label="Email" value={lead.email} />
          <Field label="Phone" value={lead.phone} />
          <Field label="Company" value={lead.company_name} />
          <Field label="Pipeline" value={masterData.pipelineName(lead.pipeline)} />
          <Field label="Current stage" value={masterData.stageName(lead.current_stage)} />
          <Field label="Source" value={masterData.sourceName(lead.source)} />
          <Field label="Total value" value={lead.total_value} />
          <Field label="Paid amount" value={lead.paid_amount} />
          <Field label="Due amount" value={lead.due_amount} />
          <Field label="Assigned to" value={assignedLabel} />
          <Field label="Created" value={lead.created_at ? new Date(lead.created_at).toLocaleString() : null} />
        </CardContent>
      </Card>

      <Separator />

      <Link to="/leads" className="text-sm text-muted-foreground hover:underline">← Back to leads</Link>

      <AssignDialog lead={lead} open={dialog === "assign"} onOpenChange={(open) => !open && setDialog(null)} />
      <ProgressDialog lead={lead} open={dialog === "progress"} onOpenChange={(open) => !open && setDialog(null)} />
      <LostDialog lead={lead} open={dialog === "lost"} onOpenChange={(open) => !open && setDialog(null)} />
      <ConvertDialog lead={lead} open={dialog === "convert"} onOpenChange={(open) => !open && setDialog(null)} />
      <ConfirmDialog open={reengageOpen} onOpenChange={setReengageOpen} title="Re-engage this lead?" description="The lead will return to ACTIVE and its lost reason/timestamp will be cleared." confirmLabel="Re-engage" loading={reengageLead.isPending} onConfirm={() => reengageLead.mutateAsync().then(() => setReengageOpen(false))} />
    </div>
  );
}
