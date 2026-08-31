import { useState } from "react";
import { useLeadPrimaryForm, useSubmitForm } from "@/features/callforms/hooks";
import DynamicFormFields from "@/features/callforms/components/DynamicFormFields";
import PageLoader from "@/components/common/PageLoader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function DynamicStageForm({ lead, onSubmitted }) {
  const primaryFormQuery = useLeadPrimaryForm(lead.id);
  const submitForm = useSubmitForm();
  const [values, setValues] = useState({});
  const [errors, setErrors] = useState({});

  if (primaryFormQuery.isLoading) return <PageLoader label="Loading stage form…" />;
  if (primaryFormQuery.isError) {
    return (
      <Card className="rounded-xl">
        <CardContent className="p-6 text-sm text-muted-foreground">Unable to load stage form.</CardContent>
      </Card>
    );
  }
  const formData = primaryFormQuery.data;
  const fields = formData?.fields ?? [];
  const isLocked = formData?.is_locked;
  const templateVersionId = formData?.template_version_id ?? formData?.template_version?.id ?? formData?.id;

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
    e.preventDefault();
    const eMap = validate();
    if (Object.keys(eMap).length) { setErrors(eMap); return; }
    setErrors({});
    try {
      await submitForm.mutateAsync({
        lead_id: lead.id,
        template_version_id: templateVersionId,
        form_data: values,
      });
      setValues({});
      onSubmitted?.();
    } catch (err) {
      void err;
    }
  };

  return (
    <Card className="rounded-xl border-[#E5E7EB] shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold">Current Stage Form — {formData.template_name ?? "Stage activity"}</CardTitle>
          <div className="flex items-center gap-2">
            {formData.version_label ? <Badge variant="outline">{formData.version_label}</Badge> : null}
            {isLocked ? <Badge className="bg-amber-50 text-amber-700 border-amber-200">Locked</Badge> : <Badge variant="secondary">Editable</Badge>}
          </div>
        </div>
        {isLocked ? <p className="text-xs text-amber-700">This version has submissions and is locked. Ask admin to clone a new version to edit fields.</p> : null}
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DynamicFormFields fields={fields} values={values} errors={errors} onChange={setValues} stepView={false} />
          <div className="sticky bottom-0 -mx-6 -mb-6 flex items-center justify-between border-t bg-white/80 px-6 py-3 backdrop-blur">
            <Button type="button" variant="outline" onClick={() => setValues({})}>Clear</Button>
            <div className="flex gap-2">
              <Button type="submit" disabled={submitForm.isPending || isLocked} className="bg-[#2563EB] hover:bg-[#1D4ED8]">
                {submitForm.isPending ? "Submitting…" : "Save draft"}
              </Button>
              <Button type="submit" disabled={submitForm.isPending || isLocked} onClick={() => { /* progress handled by parent via onSubmitted + progress button */ }}>
                {submitForm.isPending ? "Submitting…" : "Submit & progress"}
              </Button>
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
