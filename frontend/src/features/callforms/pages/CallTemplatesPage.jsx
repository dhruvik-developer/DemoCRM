// CallForms templates list + create. Row click → version editor.

import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useCallTemplates, useCreateCallTemplate } from "../hooks";
import { callTemplateSchema } from "@/schemas/callform.schema";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import FormField from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export default function CallTemplatesPage() {
  const templatesQuery = useCallTemplates();
  const createTemplate = useCreateCallTemplate();
  const [createOpen, setCreateOpen] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(callTemplateSchema) });

  const rows = templatesQuery.data ?? [];

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Call form templates</h1>
        <Button onClick={() => setCreateOpen(true)}>New template</Button>
      </div>

      {templatesQuery.isError ? (
        <PageError error={templatesQuery.error} onRetry={templatesQuery.refetch} />
      ) : (
        <DataTable
          columns={[
            {
              key: "name",
              header: "Name",
              render: (template) => (
                <Link to={`/callforms/templates/${template.id}`} className="font-medium hover:underline">
                  {template.name}
                </Link>
              ),
            },
            {
              key: "is_active",
              header: "Active",
              render: (template) => (template.is_active ? "Yes" : "No"),
            },
          ]}
          rows={rows}
          getRowId={(row) => row.id}
          isLoading={templatesQuery.isLoading}
          emptyState={<EmptyState title="No templates yet" description="Create the first call form template." />}
          page={1}
          pageSize={Math.max(rows.length, 1)}
          count={rows.length}
        />
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New call form template</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit((values) => createTemplate.mutateAsync(values).then(() => setCreateOpen(false)))} className="flex flex-col gap-3">
            <FormField id="template_name" label="Name" error={errors.name?.message}>
              <Input id="template_name" {...register("name")} />
            </FormField>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={createTemplate.isPending}>
                {createTemplate.isPending ? "Creating…" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
