/* eslint-disable react-hooks/set-state-in-effect */
// Draft creation. Backend rule: quotations are created from ACTIVE leads
// (400 otherwise). The approval requirement comes from the lead's stage.

import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm, FormProvider, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import LeadSelect from "@/features/leads/components/LeadSelect";
import LineItemsEditor from "../components/LineItemsEditor";
import { useCreateQuotation } from "../hooks";
import { createQuotationSchema } from "@/schemas/quotation.schema";
import FormField from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

import { useLeads } from "@/features/leads/hooks";

export default function QuotationCreatePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const presetLead = searchParams.get("lead") ?? "";
  const createQuotation = useCreateQuotation();
  const [leadId, setLeadId] = useState(presetLead);
  const leadsQuery = useLeads({ page_size: 50 });

  const methods = useForm({
    resolver: zodResolver(createQuotationSchema),
    defaultValues: {
      lead_id: presetLead || "",
      terms: "",
      notes: "",
      line_items: [{ description: "", quantity: 1, unit_price: "" }],
    },
  });

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors },
  } = methods;

  const watchedLeadId = useWatch({ control, name: "lead_id" });
  const effectiveLead = leadId || watchedLeadId;

  useEffect(() => {
    if (presetLead) {
      setValue("lead_id", presetLead);
      setLeadId(presetLead);
    }
  }, [presetLead, setValue]);
  const selectedLead = (leadsQuery.data?.results ?? []).find(
    (l) => String(l.id) === String(effectiveLead),
  );

  const onSubmit = async (values) => {
    try {
      const quotation = await createQuotation.mutateAsync({
        lead_id: effectiveLead || values.lead_id,
        terms: values.terms || undefined,
        notes: values.notes || undefined,
        line_items: values.line_items.length
          ? values.line_items
          : undefined,
      });
      navigate(`/quotations/${quotation.id}`);
    } catch {
      // Toasted by the mutation; form stays filled for retry.
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">New quotation</h1>
        <Button variant="ghost" asChild>
          <Link to="/quotations">Cancel</Link>
        </Button>
      </div>

      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <FormField id="lead_id" label="Lead" error={errors.lead_id?.message}
            help="Must be an ACTIVE lead. Approval is decided by the lead's current stage."
          >
            {presetLead ? (
              <Input id="lead_id" value={presetLead} disabled />
            ) : (
              <LeadSelect
                value={effectiveLead}
                onChange={(value) => {
                  setLeadId(value);
                  setValue("lead_id", value);
                }}
              />
            )}
            {selectedLead ? (
              <div className="mt-2 rounded-md border bg-muted/30 p-3 text-sm flex flex-col gap-1">
                <span className="font-semibold text-xs text-muted-foreground uppercase tracking-wider">
                  Selected Lead
                </span>
                <div>
                  <span className="font-medium text-muted-foreground">Lead ID: </span>
                  <span className="font-mono">{selectedLead.id}</span>
                </div>
                <div>
                  <span className="font-medium text-muted-foreground">Lead Name: </span>
                  <span className="font-medium">{selectedLead.name}</span>
                </div>
                {selectedLead.company_name ? (
                  <div>
                    <span className="font-medium text-muted-foreground">Company: </span>
                    <span>{selectedLead.company_name}</span>
                  </div>
                ) : null}
              </div>
            ) : null}
          </FormField>

          <FormField id="terms" label="Terms">
            <Textarea id="terms" rows={3} {...register("terms")} />
          </FormField>

          <FormField id="notes" label="Notes">
            <Textarea id="notes" rows={2} {...register("notes")} />
          </FormField>

          <div>
            <h2 className="mb-2 text-sm font-medium">Line items</h2>
            <LineItemsEditor />
          </div>

          <Button type="submit" disabled={createQuotation.isPending} className="self-start">
            {createQuotation.isPending ? "Creating…" : "Create draft"}
          </Button>
        </form>
      </FormProvider>
    </div>
  );
}
