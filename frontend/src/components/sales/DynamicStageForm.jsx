import { useState } from "react";
import { useLeadPrimaryForm, useLeadStageForms, useSubmitForm, useCreateAdhocProposal } from "@/features/callforms/hooks";
import { useProgressLead } from "@/features/leads/hooks";
import { usePipelineStages } from "@/features/crm/hooks";
import DynamicFormFields from "@/features/callforms/components/DynamicFormFields";
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
  const [proposeOpen, setProposeOpen] = useState(false);
  const proposalTypes = ["text", "textarea", "number", "boolean", "date", "time", "datetime", "select", "radio", "checkbox", "file"];
  const [proposal, setProposal] = useState({ field_key: "", label: "", field_type: "text", options_text: "", file_types: "" });
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
  // Stacked multi-form: render all stageForms directly, don't use baseFields
  if (hasMulti) {
    const hasAnyFields = stageForms.some((f) => (f.fields ?? []).length > 0) || adhocFields.length > 0;
    if (!hasAnyFields) {
      return (
        <Card className="rounded-xl border-dashed">
          <CardHeader><CardTitle className="text-sm">Current Stage Form</CardTitle></CardHeader>
          <CardContent><p className="text-sm text-muted-foreground">No form configured for this stage. Ask an admin to link a Call Template to the stage via <code className="rounded bg-muted px-1">Stage Activities</code>.</p></CardContent>
        </Card>
      );
    }
    // stacked rendering handled below — skip single-form baseFields
  }
  const formData = hasMulti ? null : primaryFormQuery.data;
  // Normalize fields shape for single case
  const baseFields = hasMulti ? [] : (formData?.fields ?? []);
  const fields = [...baseFields, ...adhocFields];
  const isLocked = formData?.is_locked ?? formData?.template_version?.is_locked;
  const templateVersionId = formData?.template_version_id ?? formData?.template_version?.id ?? formData?.id;
  const activity = formData?.activity;

  if (!hasMulti && !fields.length) {
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

  // Stacked mode — one card per form, no tabs
  if (hasMulti) {
    return (
      <div className="flex flex-col gap-4">
        {stageForms.map((f) => {
          const fFields = [...(f.fields ?? []), ...adhocFields];
          const fLocked = f.template_version?.is_locked;
          const fVid = f.template_version?.id;
          const fActivity = f.activity;
          return (
            <Card key={f.activity.id} className="rounded-[14px] border-[#E2E8F0] shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle className="text-sm font-bold">{fActivity?.name ?? "Stage activity"} <Badge variant="secondary" className="ml-2 text-[11px]">{fActivity?.form_type ?? "CALL"}</Badge> {fActivity?.is_primary ? <Badge variant="outline" className="ml-1 text-[11px]">primary</Badge> : null}</CardTitle>
                    <div className="mt-1 text-[11px] text-muted-foreground">Configured schema: {f.template_version?.version_label ?? "v1"} · {fLocked ? "Locked" : "Active & Editable"}</div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {f.template_version?.version_label ? <Badge variant="outline" className="text-[11px]">{f.template_version.version_label}</Badge> : null}
                    {fLocked ? <Badge className="bg-amber-50 text-amber-700 border-amber-200 text-[11px] font-bold">Locked</Badge> : <Badge className="bg-primary-soft text-primary border-transparent text-[11px] font-bold">Live Entry</Badge>}
                  </div>
                </div>
                {fLocked ? <p className="text-xs text-amber-700">This version has submissions and is locked. Ask admin to clone a new version to edit fields.</p> : null}
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                  <DynamicFormFields fields={fFields} values={values} errors={errors} onChange={setValues} stepView={false} onDelete={(key) => setAdhocFields((prev) => prev.filter((f) => f.field_key !== key))} />
                  <div className="flex justify-start">
                    <Button type="button" variant="ghost" size="sm" onClick={() => setProposeOpen(true)}>+ Propose new field</Button>
                  </div>
                  <div className="sticky bottom-0 -mx-6 -mb-6 flex items-center justify-between border-t border-[#F1F5F9] bg-white/80 px-6 py-3 backdrop-blur">
                    <span className="text-[11.5px] text-muted-foreground hidden sm:block">Fields are autosynced with backend.</span>
                    <div className="flex gap-2 ml-auto">
                      <Button type="button" variant="outline" onClick={() => setValues({})}>Clear</Button>
                      <Button type="button" disabled={submitForm.isPending || fLocked} onClick={async (e) => { e.preventDefault(); const em=validate(); if(Object.keys(em).length){setErrors(em);return;} setErrors({}); try{ await submitForm.mutateAsync({lead_id: lead.id, template_version_id: fVid, data: values}); setValues({}); onSubmitted?.(); } catch { /* toast */ } }} className="bg-secondary hover:bg-[#E0532A]">
                        {submitForm.isPending ? "Submitting…" : "Save draft"}
                      </Button>
                      <Button type="button" disabled={submitForm.isPending || progressLead.isPending || fLocked} onClick={async (e) => { e.preventDefault(); const em=validate(); if(Object.keys(em).length){setErrors(em);return;} setErrors({}); try{ await submitForm.mutateAsync({lead_id: lead.id, template_version_id: fVid, data: values}); const stages = stagesQ.data ?? []; const idx = stages.findIndex((s) => s.id === lead.current_stage); const nextId = stages[idx + 1]?.id; if (nextId) await progressLead.mutateAsync(nextId); setValues({}); onSubmitted?.(); } catch { /* toast */ }}} className="bg-secondary hover:bg-[#E0532A]">
                        Submit & progress →
                      </Button>
                    </div>
                  </div>
                </form>
              </CardContent>
            </Card>
          );
        })}
        <Dialog open={proposeOpen} onOpenChange={setProposeOpen}>
          <DialogContent>
            <DialogHeader><DialogTitle>Propose new field</DialogTitle></DialogHeader>
            <p className="text-xs text-muted-foreground">Employee can propose a field during call — Admin/Manager reviews in <code>CallForms → Adhoc</code> then approves to add to template.</p>
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1"><label className="text-xs font-medium">Field key (a-z0-9_)</label><Input value={proposal.field_key} onChange={(e) => setProposal({ ...proposal, field_key: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "") })} placeholder="e.g. alternate_phone" /></div>
              <div className="flex flex-col gap-1"><label className="text-xs font-medium">Label</label><Input value={proposal.label} onChange={(e) => setProposal({ ...proposal, label: e.target.value })} placeholder="Alternate Phone" /></div>
              <div className="flex flex-col gap-1"><label className="text-xs font-medium">Type</label><Select value={proposal.field_type} onValueChange={(v) => setProposal({ ...proposal, field_type: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{proposalTypes.map((t) => <SelectItem key={t} value={t} className="capitalize">{t}</SelectItem>)}</SelectContent></Select></div>
              {["select", "radio", "checkbox"].includes(proposal.field_type) ? (
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium">Options <span className="text-destructive">*</span></label>
                  <Input value={proposal.options_text} onChange={(e) => setProposal({ ...proposal, options_text: e.target.value })} placeholder="e.g. Low, Medium, High" />
                </div>
              ) : null}
              {proposal.field_type === "file" ? (
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium">File types</label>
                  <Input value={proposal.file_types} onChange={(e) => setProposal({ ...proposal, file_types: e.target.value })} placeholder="e.g. pdf,docx,jpg" />
                </div>
              ) : null}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setProposeOpen(false)}>Cancel</Button>
              <Button disabled={!proposal.field_key || !proposal.label || (["select","radio","checkbox"].includes(proposal.field_type) && !proposal.options_text.trim()) || createProposal.isPending} onClick={async () => {
                try {
                  const payload = { template_version: stageForms[0]?.template_version?.id ?? templateVersionId, field_key: proposal.field_key, label: proposal.label, field_type: proposal.field_type, options: ["select","radio","checkbox"].includes(proposal.field_type) ? proposal.options_text.split(",").map((s)=>s.trim()).filter(Boolean) : undefined, file_types: proposal.field_type === "file" ? proposal.file_types : undefined };
                  await createProposal.mutateAsync(payload);
                  const opts = payload.options; const vr={}; if(payload.file_types) vr.file_types=payload.file_types; setAdhocFields((prev) => [...prev, { field_key: proposal.field_key, label: proposal.label, field_type: proposal.field_type, is_required: false, options: opts, validation_rules: vr, id: `adhoc_${proposal.field_key}` }]);
                  setProposeOpen(false); setProposal({ field_key: "", label: "", field_type: "text", options_text: "", file_types: "" });
                } catch (err) { void err; }
              }}>{createProposal.isPending ? "Proposing…" : "Propose"}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  }
  // Single form fallback below
  const isEditableRestricted = Boolean(activity?.editable_roles?.length && false);

  return (
    <>
      <Card className="rounded-[14px] border-[#E2E8F0] shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle className="text-sm font-bold">Current Stage Form — {formData?.template_name ?? formData?.activity?.name ?? "Stage activity"} </CardTitle>
              <div className="mt-1 text-[11px] text-muted-foreground">Configured schema: {(formData?.version_label ?? formData?.template_version?.version_label) ?? "v1"} · {isLocked ? "Locked" : "Active & Editable"}</div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {(formData?.version_label ?? formData?.template_version?.version_label) ? <Badge variant="outline" className="text-[11px]">{formData?.version_label ?? formData?.template_version?.version_label}</Badge> : null}
              {isLocked ? <Badge className="bg-amber-50 text-amber-700 border-amber-200 text-[11px] font-bold">Locked</Badge> : <Badge className="bg-primary-soft text-primary border-transparent text-[11px] font-bold">Live Entry</Badge>}
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
          <div className="sticky bottom-0 -mx-6 -mb-6 flex items-center justify-between border-t border-[#F1F5F9] bg-white/80 px-6 py-3 backdrop-blur">
            <span className="text-[11.5px] text-muted-foreground hidden sm:block">Fields are autosynced with backend.</span>
            <div className="flex gap-2 ml-auto">
              <Button type="button" variant="outline" onClick={() => setValues({})}>Clear</Button>
              <Button type="button" disabled={submitForm.isPending || isLocked} onClick={handleSubmit} className="bg-secondary hover:bg-[#E0532A]">
                {submitForm.isPending ? "Submitting…" : "Save draft"}
              </Button>
              <Button type="button" disabled={submitForm.isPending || progressLead.isPending || isLocked} onClick={handleSubmitAndProgress} className="bg-secondary hover:bg-[#E0532A]">
                {submitForm.isPending || progressLead.isPending ? "Submitting…" : "Submit & progress →"}
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
            <div className="flex flex-col gap-1"><label className="text-xs font-medium">Type</label><Select value={proposal.field_type} onValueChange={(v) => setProposal({ ...proposal, field_type: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{proposalTypes.map((t) => <SelectItem key={t} value={t} className="capitalize">{t}</SelectItem>)}</SelectContent></Select></div>
            {["select", "radio", "checkbox"].includes(proposal.field_type) ? (
              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium">Options <span className="text-destructive">*</span> <span className="font-normal text-muted-foreground">(comma separated)</span></label>
                <Input value={proposal.options_text} onChange={(e) => setProposal({ ...proposal, options_text: e.target.value })} placeholder="e.g. Low, Medium, High" />
                <p className="text-xs text-muted-foreground">Required for select/radio/checkbox. Chips allow edit/delete like admin form.</p>
              </div>
            ) : null}
            {proposal.field_type === "file" ? (
              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium">File types</label>
                <Input value={proposal.file_types} onChange={(e) => setProposal({ ...proposal, file_types: e.target.value })} placeholder="e.g. pdf,docx,jpg" />
                <p className="text-xs text-muted-foreground">Comma exts without dot. Shown only for file.</p>
              </div>
            ) : null}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setProposeOpen(false)}>Cancel</Button>
            <Button disabled={!proposal.field_key || !proposal.label || (["select","radio","checkbox"].includes(proposal.field_type) && !proposal.options_text.trim()) || createProposal.isPending} onClick={async () => {
              try {
                const payload = {
                  template_version: templateVersionId,
                  field_key: proposal.field_key,
                  label: proposal.label,
                  field_type: proposal.field_type,
                  options: ["select","radio","checkbox"].includes(proposal.field_type) ? proposal.options_text.split(",").map((s)=>s.trim()).filter(Boolean) : undefined,
                  file_types: proposal.field_type === "file" ? proposal.file_types : undefined,
                };
                await createProposal.mutateAsync(payload);
                // immediate temporary for this call — appears below current fields with chips
                const opts = payload.options;
                const validation_rules = {};
                if (payload.file_types) validation_rules.file_types = payload.file_types;
                setAdhocFields((prev) => [...prev, { field_key: proposal.field_key, label: proposal.label, field_type: proposal.field_type, is_required: false, options: opts, validation_rules, id: `adhoc_${proposal.field_key}` }]);
                setProposeOpen(false); setProposal({ field_key: "", label: "", field_type: "text", options_text: "", file_types: "" });
              } catch (err) { void err; }
            }}>{createProposal.isPending ? "Proposing…" : "Propose"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
