import { useState } from "react";
import { useLeadPrimaryForm, useLeadStageForms, useSubmitForm, useCreateAdhocProposal } from "@/features/callforms/hooks";
import { useProgressLead } from "@/features/leads/hooks";
import { usePipelineStages } from "@/features/crm/hooks";
import DynamicFormFields from "@/features/callforms/components/DynamicFormFields";
import EmptyState from "@/components/common/EmptyState";
import PageLoader from "@/components/common/PageLoader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function DynamicStageForm({ lead, onSubmitted }) {
  const primaryFormQuery = useLeadPrimaryForm(lead.id);
  const stageFormsQuery = useLeadStageForms(lead.id);
  const submitForm = useSubmitForm();
  const progressLead = useProgressLead(lead.id);
  const stagesQ = usePipelineStages(lead.pipeline);
  const [values, setValues] = useState({});
  const [errors, setErrors] = useState({});
  const [activeIdx, setActiveIdx] = useState(0);
  const [proposeOpen, setProposeOpen] = useState(false);
  const [proposal, setProposal] = useState({ field_key: "", label: "", field_type: "text" });
  const [adhocFields, setAdhocFields] = useState([]);
  const createProposal = useCreateAdhocProposal();

  if (primaryFormQuery.isLoading || stageFormsQuery.isLoading) return <PageLoader label="Loading stage form…" />;
  if (primaryFormQuery.isError && stageFormsQuery.isError) {
    return (
      <Card className="rounded-xl">
        <CardContent className="p-6 text-sm text-muted-foreground">Unable to load stage form.</CardContent>
      </Card>
    );
  }
  const stageForms = stageFormsQuery.data?.forms ?? [];
  const hasMulti = stageForms.length > 1;
  // Prefer multi-form data if available (role-filtered), otherwise fallback to primary
  const activeForm = hasMulti ? stageForms[activeIdx] : null;
  const formData = hasMulti ? activeForm : primaryFormQuery.data;
  // Handle EmptyState when all forms filtered by allowed_roles
  if (hasMulti && !activeForm) {
    return (
      <EmptyState title="Access restricted — contact your manager" description="Your role is not allowed to view forms in this stage (allowed_roles)." />
    );
  }
  // Normalize fields shape for both sources
  const baseFields = hasMulti ? (activeForm?.fields ?? []) : (formData?.fields ?? []);
  const fields = [...baseFields, ...adhocFields];
  const isLocked = hasMulti ? activeForm?.template_version?.is_locked : formData?.is_locked ?? formData?.template_version?.is_locked;
  const templateVersionId = hasMulti ? activeForm?.template_version?.id : (formData?.template_version_id ?? formData?.template_version?.id ?? formData?.id);
  const activity = hasMulti ? activeForm?.activity : formData?.activity;

  if (!fields.length) {
    return (
      <Card className="rounded-xl border-dashed">
        <CardHeader>
          <CardTitle className="text-sm">Current Stage Form</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No form configured for this stage. Ask an admin to link a Call Template to the stage via <code className="rounded bg-muted px-1">Stage Activities</code>.
          </p>
        </CardContent>
      </Card>
    );
  }

  const validate = () => {
    const e = {};
    for (const f of fields) if (f.is_required && (values[f.field_key] === "" || values[f.field_key] == null)) e[f.field_key] = `${f.label} is required.`;
    return e;
  };

  const handleSubmit = async (e) => {
    e?.preventDefault();
    const eMap = validate();
    if (Object.keys(eMap).length) { setErrors(eMap); return; }
    setErrors({});
    try {
      await submitForm.mutateAsync({
        lead_id: lead.id,
        template_version_id: templateVersionId,
        data: values,
      });
      setValues({});
      onSubmitted?.();
    } catch (err) {
      void err;
    }
  };

  const handleSubmitAndProgress = async (e) => {
    e.preventDefault();
    const eMap = validate();
    if (Object.keys(eMap).length) { setErrors(eMap); return; }
    setErrors({});
    try {
      await submitForm.mutateAsync({
        lead_id: lead.id,
        template_version_id: templateVersionId,
        data: values,
      });
      // progress to next stage
      const stages = stagesQ.data ?? [];
      const idx = stages.findIndex((s) => s.id === lead.current_stage);
      const nextId = stages[idx + 1]?.id;
      if (nextId) await progressLead.mutateAsync(nextId);
      setValues({});
      onSubmitted?.();
    } catch (err) {
      void err;
    }
  };

  // Check editable_roles for current user (server also enforces)
  const isEditableRestricted = Boolean(activity?.editable_roles?.length && false); // placeholder, server filters allowed_roles; editable check is server-side

  return (
    <>
      {hasMulti ? (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {stageForms.map((f, idx) => (
            <Button key={f.activity.id} size="sm" variant={idx === activeIdx ? "default" : "outline"} onClick={() => { setActiveIdx(idx); setValues({}); setErrors({}); }}>
              {f.activity.form_type ?? f.activity.name} {f.activity.is_primary ? "★" : ""}
            </Button>
          ))}
        </div>
      ) : null}
      <Card className="rounded-xl border-[#E5E7EB] shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold">Current Stage Form — {hasMulti ? (activeForm?.activity?.name ?? "Stage activity") : (formData?.template_name ?? formData?.activity?.name ?? "Stage activity")} {hasMulti ? <Badge variant="secondary" className="ml-2">{activeForm?.activity?.form_type}</Badge> : null}</CardTitle>
            <div className="flex items-center gap-2">
              {(hasMulti ? activeForm?.template_version?.version_label : formData?.version_label ?? formData?.template_version?.version_label) ? <Badge variant="outline">{hasMulti ? activeForm?.template_version?.version_label : (formData?.version_label ?? formData?.template_version?.version_label)}</Badge> : null}
              {isLocked ? <Badge className="bg-amber-50 text-amber-700 border-amber-200">Locked</Badge> : <Badge variant="secondary">Editable</Badge>}
            </div>
          </div>
          {isLocked ? <p className="text-xs text-amber-700">This version has submissions and is locked. Ask admin to clone a new version to edit fields.</p> : null}
          {isEditableRestricted ? <p className="text-xs text-red-600">Access restricted — contact your manager (editable_roles).</p> : null}
        </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DynamicFormFields fields={fields} values={values} errors={errors} onChange={setValues} stepView={false} onDelete={(key) => setAdhocFields((prev) => prev.filter((f) => f.field_key !== key))} />
          <div className="flex justify-start">
            <Button type="button" variant="ghost" size="sm" onClick={() => setProposeOpen(true)}>+ Propose new field</Button>
          </div>
          <div className="sticky bottom-0 -mx-6 -mb-6 flex items-center justify-between border-t bg-white/80 px-6 py-3 backdrop-blur">
            <Button type="button" variant="outline" onClick={() => setValues({})}>Clear</Button>
            <div className="flex gap-2">
              <Button type="button" disabled={submitForm.isPending || isLocked} onClick={handleSubmit} className="bg-[#2563EB] hover:bg-[#1D4ED8]">
                {submitForm.isPending ? "Submitting…" : "Save draft"}
              </Button>
              <Button type="button" disabled={submitForm.isPending || progressLead.isPending || isLocked} onClick={handleSubmitAndProgress} className="bg-[#2563EB] hover:bg-[#1D4ED8]">
                {submitForm.isPending || progressLead.isPending ? "Submitting…" : "Submit & progress"}
              </Button>
            </div>
          </div>
        </form>
      </CardContent>
      </Card>
      <Dialog open={proposeOpen} onOpenChange={setProposeOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Propose new field</DialogTitle></DialogHeader>
          <p className="text-xs text-muted-foreground">Employee can propose a field during call — Admin/Manager reviews in <code>CallForms → Adhoc</code> then approves to add to template.</p>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1"><label className="text-xs font-medium">Field key (a-z0-9_)</label><Input value={proposal.field_key} onChange={(e) => setProposal({ ...proposal, field_key: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "") })} placeholder="e.g. alternate_phone" /></div>
            <div className="flex flex-col gap-1"><label className="text-xs font-medium">Label</label><Input value={proposal.label} onChange={(e) => setProposal({ ...proposal, label: e.target.value })} placeholder="Alternate Phone" /></div>
            <div className="flex flex-col gap-1"><label className="text-xs font-medium">Type</label><Select value={proposal.field_type} onValueChange={(v) => setProposal({ ...proposal, field_type: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="text">text</SelectItem><SelectItem value="textarea">textarea</SelectItem><SelectItem value="number">number</SelectItem><SelectItem value="select">select</SelectItem><SelectItem value="date">date</SelectItem></SelectContent></Select></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setProposeOpen(false)}>Cancel</Button>
            <Button disabled={!proposal.field_key || !proposal.label || createProposal.isPending} onClick={async () => {
              try {
                await createProposal.mutateAsync({ template_version: templateVersionId, field_key: proposal.field_key, label: proposal.label, field_type: proposal.field_type });
                // immediate temporary for this call — appears below current fields
                setAdhocFields((prev) => [...prev, { field_key: proposal.field_key, label: proposal.label, field_type: proposal.field_type, is_required: false, id: `adhoc_${proposal.field_key}` }]);
                setProposeOpen(false); setProposal({ field_key: "", label: "", field_type: "text" });
              } catch (err) { void err; }
            }}>{createProposal.isPending ? "Proposing…" : "Propose"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
