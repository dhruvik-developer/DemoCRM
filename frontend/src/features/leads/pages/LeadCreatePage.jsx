// Lead create. Backend rule (CRMService.create_lead): a new lead must start at
// the pipeline's FIRST stage — so the form auto-selects it instead of asking,
// and inactive master data is hidden from the selects.

import { useEffect, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useLeadSources, usePipelines, usePipelineStages } from "@/features/crm/hooks";
import { useCreateLead } from "../hooks";
import { leadSchema } from "@/schemas/lead.schema";
import FormField from "@/components/forms/FormField";
import PageError from "@/components/common/PageError";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getApiErrorMessage } from "@/utils/errors";

import { useUsers } from "@/features/admin/hooks";

export default function LeadCreatePage() {
  const navigate = useNavigate();
  const createLead = useCreateLead();

  const sourcesQuery = useLeadSources();
  const pipelinesQuery = usePipelines();
  const usersQuery = useUsers();

  const {
    register,
    handleSubmit,
    setValue,
    control,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(leadSchema),
    defaultValues: {
      name: "",
      email: "",
      phone: "",
      company_name: "",
      source: "",
      pipeline: "",
      assigned_to: "",
      total_value: "",
    },
  });

  const pipelineId = useWatch({ control, name: "pipeline" });
  const sourceValue = useWatch({ control, name: "source" });
  const assignedToValue = useWatch({ control, name: "assigned_to" });
  const stagesQuery = usePipelineStages(pipelineId);
  const firstStage = useMemo(() => stagesQuery.data?.[0], [stagesQuery.data]);

  // Backend enforces the first stage on create — keep it in sync.
  useEffect(() => {
    if (pipelineId && firstStage) {
      setValue("current_stage", firstStage.id);
    }
  }, [pipelineId, firstStage, setValue]);

  const onSubmit = async (values) => {
    try {
      const payload = {
        name: values.name,
        email: values.email || undefined,
        phone: values.phone || undefined,
        company_name: values.company_name || undefined,
        source: values.source,
        pipeline: values.pipeline,
        current_stage: firstStage?.id,
        assigned_to: values.assigned_to || undefined,
        total_value: values.total_value === "" ? undefined : values.total_value,
      };
      await createLead.mutateAsync(payload);
      navigate("/leads");
    } catch (error) {
      const normalized = error.normalized ?? {
        fieldErrors: {},
        message: getApiErrorMessage(error),
      };
      for (const [field, messages] of Object.entries(normalized.fieldErrors)) {
        if (field in leadSchema.shape) {
          setError(field, { message: messages[0] });
        }
      }
    }
  };

  if (sourcesQuery.isError || pipelinesQuery.isError) {
    return (
      <PageError
        error={sourcesQuery.error ?? pipelinesQuery.error}
        onRetry={() => {
          sourcesQuery.refetch();
          pipelinesQuery.refetch();
        }}
      />
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">New lead</h1>
        <Button variant="ghost" asChild>
          <Link to="/leads">Cancel</Link>
        </Button>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <FormField id="name" label="Name" error={errors.name?.message}>
          <Input id="name" {...register("name")} />
        </FormField>

        <div className="grid gap-4 md:grid-cols-2">
          <FormField id="email" label="Email" error={errors.email?.message}>
            <Input id="email" type="email" {...register("email")} />
          </FormField>
          <FormField id="phone" label="Phone" error={errors.phone?.message}>
            <Input id="phone" {...register("phone")} />
          </FormField>
        </div>

        <FormField id="company_name" label="Company" error={errors.company_name?.message}>
          <Input id="company_name" {...register("company_name")} />
        </FormField>

        <div className="grid gap-4 md:grid-cols-2">
          <FormField id="source" label="Lead source" error={errors.source?.message}>
            <Select value={sourceValue} onValueChange={(value) => setValue("source", value)}>
              <SelectTrigger>
                <SelectValue placeholder="Select source" />
              </SelectTrigger>
              <SelectContent>
                {(sourcesQuery.data ?? [])
                  .filter((source) => source.is_active)
                  .map((source) => (
                    <SelectItem key={source.id} value={source.id}>
                      {source.name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </FormField>

          <FormField id="assigned_to" label="Assigned To" error={errors.assigned_to?.message}>
            <Select
              value={assignedToValue || ""}
              onValueChange={(value) => setValue("assigned_to", value)}
            >
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
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <FormField id="pipeline" label="Pipeline" error={errors.pipeline?.message}>
            <Select
              value={pipelineId}
              onValueChange={(value) => setValue("pipeline", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select pipeline" />
              </SelectTrigger>
              <SelectContent>
                {(pipelinesQuery.data ?? [])
                  .filter((pipeline) => pipeline.is_active)
                  .map((pipeline) => (
                    <SelectItem key={pipeline.id} value={pipeline.id}>
                      {pipeline.name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </FormField>

          <FormField
            id="current_stage"
            label="Stage"
            help="New leads start at the pipeline's first stage."
          >
            <Input
              id="current_stage"
              value={firstStage ? `${firstStage.name}` : pipelineId ? "…" : "—"}
              disabled
            />
          </FormField>
        </div>

        <FormField id="total_value" label="Total value" error={errors.total_value?.message}>
          <Input id="total_value" inputMode="decimal" placeholder="0.00" {...register("total_value")} />
        </FormField>

        <Button type="submit" disabled={createLead.isPending} className="self-start">
          {createLead.isPending ? "Creating…" : "Create lead"}
        </Button>
      </form>
    </div>
  );
}
