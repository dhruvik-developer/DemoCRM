// Template detail: versions + primary selection + per-version field editor
// + submission analytics. A version with submissions is LOCKED — the editor
// is disabled with a banner (the backend 400s mutations anyway).

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  useCallTemplate,
  useCloneVersion,
  useCreateField,
  useCreateVersion,
  useDeleteField,
  useFields,
  useReorderFields,
  useSetPrimaryVersion,
  useSubmissionAnalytics,
  useVersions,
} from "../hooks";
import { callFieldSchema } from "@/schemas/callform.schema";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import FormField from "@/components/forms/FormField";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const FIELD_TYPES = ["text", "textarea", "number", "boolean", "date", "time", "select"];

const EMPTY_FIELD_FORM = {
  field_key: "",
  label: "",
  field_type: "text",
  is_required: false,
  help_text: "",
  options_text: "",
};

function FieldEditor({ version }) {
  const fieldsQuery = useFields(version.id);
  const createField = useCreateField();
  const deleteField = useDeleteField();
  const reorder = useReorderFields();
  const [form, setForm] = useState(EMPTY_FIELD_FORM);
  const [formError, setFormError] = useState("");

  const locked = version.is_locked;
  const fields = [...(fieldsQuery.data ?? [])].sort(
    (a, b) => a.display_order - b.display_order,
  );

  const move = async (index, direction) => {
    const next = [...fields];
    const target = index + direction;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    await reorder.mutateAsync({
      templateVersionId: version.id,
      orders: next.map((field, order) => ({
        field_id: field.id,
        display_order: order + 1,
      })),
    });
  };

  const onCreate = async (event) => {
    event.preventDefault();
    setFormError("");
    const parsed = callFieldSchema.safeParse(form); // mirrors serializer rules
    if (!parsed.success) {
      setFormError(parsed.error.issues[0]?.message ?? "Invalid field.");
      return;
    }
    try {
      await createField.mutateAsync({
        template_version: version.id,
        field_key: form.field_key,
        label: form.label,
        field_type: form.field_type,
        is_required: form.is_required,
        help_text: form.help_text || undefined,
        options:
          form.field_type === "select"
            ? form.options_text.split(",").map((option) => option.trim()).filter(Boolean)
            : undefined,
      });
      setForm(EMPTY_FIELD_FORM);
    } catch {
      // Toasted by the mutation.
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">
          Fields — v{version.version_number}
          {version.is_primary ? <Badge className="ml-2">primary</Badge> : null}
        </CardTitle>
        {locked ? <Badge variant="destructive">Locked (has submissions)</Badge> : null}
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {locked ? (
          <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            This version has submissions and is read-only. Clone it to make changes.
          </p>
        ) : null}

        <div className="flex flex-col gap-2">
          {(fieldsQuery.data ?? []).length === 0 && !fieldsQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">No fields yet.</p>
          ) : null}
          {fields.map((field, index) => (
            <div key={field.id} className="flex items-center gap-2 rounded-md border p-2 text-sm">
              <span className="font-mono text-xs text-muted-foreground">{field.field_key}</span>
              <span className="font-medium">{field.label}</span>
              <Badge variant="outline">{field.field_type}</Badge>
              {field.is_required ? <Badge variant="secondary">required</Badge> : null}
              <div className="ml-auto flex gap-1">
                <Button variant="ghost" size="sm" disabled={locked || index === 0} onClick={() => move(index, -1)}>
                  ↑
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={locked || index === fields.length - 1}
                  onClick={() => move(index, 1)}
                >
                  ↓
                </Button>
                {!locked ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => deleteField.mutateAsync(field.id)}
                  >
                    ✕
                  </Button>
                ) : null}
              </div>
            </div>
          ))}
        </div>

        {!locked ? (
          <form onSubmit={onCreate} className="grid gap-3 md:grid-cols-6">
            <FormField id="f_key" label="Key">
              <Input
                id="f_key"
                placeholder="e.g. interested"
                value={form.field_key}
                onChange={(e) => setForm({ ...form, field_key: e.target.value })}
              />
            </FormField>
            <FormField id="f_label" label="Label">
              <Input id="f_label" value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
            </FormField>
            <FormField id="f_type" label="Type">
              <Select value={form.field_type} onValueChange={(value) => setForm({ ...form, field_type: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {FIELD_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>{type}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField id="f_options" label="Options (select only)">
              <Input
                id="f_options"
                placeholder="a,b,c"
                value={form.options_text}
                onChange={(e) => setForm({ ...form, options_text: e.target.value })}
                disabled={form.field_type !== "select"}
              />
            </FormField>
            <label className="mt-6 flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="h-4 w-4"
                checked={form.is_required}
                onChange={(e) => setForm({ ...form, is_required: e.target.checked })}
              />
              Required
            </label>
            <Button type="submit" className="self-end" disabled={createField.isPending}>
              Add field
            </Button>

            {formError ? (
              <p role="alert" className="text-sm text-destructive md:col-span-6">
                {formError}
              </p>
            ) : null}
          </form>
        ) : null}
      </CardContent>
    </Card>
  );
}

function VersionAnalytics({ versionId }) {
  const analyticsQuery = useSubmissionAnalytics(versionId);
  if (analyticsQuery.isLoading || analyticsQuery.isError || !analyticsQuery.data) {
    return null;
  }

  const raw = analyticsQuery.data;
  const rows = Array.isArray(raw)
    ? raw
    : Object.entries(raw).map(([field_key, info]) => ({ field_key, ...info }));
  if (!rows.length) return null;

  const metricKey =
    Object.keys(rows[0]).find(
      (key) => key !== "field_key" && typeof rows[0][key] === "number",
    ) ?? Object.keys(rows[0]).find((key) => key !== "field_key");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Submission analytics</CardTitle>
      </CardHeader>
      <CardContent className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="field_key" fontSize={12} />
            <YAxis allowDecimals={false} fontSize={12} />
            <Tooltip />
            <Bar dataKey={metricKey} fill="#7c3aed" radius={4} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export default function CallTemplateDetailPage() {
  const { templateId } = useParams();
  const templateQuery = useCallTemplate(templateId);
  const versionsQuery = useVersions(templateId);
  const createVersion = useCreateVersion();
  const cloneVersionMutation = useCloneVersion();
  const setPrimary = useSetPrimaryVersion();

  const [selectedVersionId, setSelectedVersionId] = useState(null);

  if (templateQuery.isLoading) return <PageLoader label="Loading template…" />;
  if (templateQuery.isError) {
    return <PageError error={templateQuery.error} onRetry={templateQuery.refetch} />;
  }

  const template = templateQuery.data;
  const versions = versionsQuery.data ?? [];
  const selected =
    versions.find((version) => version.id === selectedVersionId) ??
    versions.find((version) => version.is_primary) ??
    versions[0];

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">{template.name}</h1>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={createVersion.isPending}
            onClick={() => createVersion.mutateAsync({ templateId: template.id, version_label: "" })}
          >
            New version
          </Button>
          {selected ? (
            <>
              <Button
                variant="outline"
                size="sm"
                disabled={cloneVersionMutation.isPending}
                onClick={() => cloneVersionMutation.mutateAsync({ versionId: selected.id })}
              >
                Clone v{selected.version_number}
              </Button>
              {!selected.is_primary ? (
                <Button
                  size="sm"
                  disabled={setPrimary.isPending}
                  onClick={() =>
                    setPrimary.mutateAsync({ templateId: template.id, versionId: selected.id })
                  }
                >
                  Set primary
                </Button>
              ) : null}
            </>
          ) : null}
          <Button variant="ghost" asChild>
            <Link to="/callforms">← Templates</Link>
          </Button>
        </div>
      </div>

      {versions.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No versions yet — click “New version” to create v1.
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted-foreground">Editing:</span>
            <Select
              value={selected?.id ?? ""}
              onValueChange={(value) => setSelectedVersionId(value)}
            >
              <SelectTrigger className="w-64">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {versions.map((version) => (
                  <SelectItem key={version.id} value={version.id}>
                    v{version.version_number} {version.is_primary ? "(primary)" : ""}
                    {version.is_locked ? " 🔒" : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selected ? <FieldEditor key={selected.id} version={selected} /> : null}
          {selected ? <VersionAnalytics versionId={selected.id} /> : null}
        </>
      )}
    </div>
  );
}
