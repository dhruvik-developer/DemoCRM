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
  useCreateFieldMapping,
  useCreateVersion,
  useDeleteField,
  useDeleteFieldMapping,
  useFieldMappings,
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

const FIELD_TYPES = ["text", "textarea", "number", "boolean", "date", "time", "datetime", "select", "radio", "checkbox", "file"];

const EMPTY_FIELD_FORM = {
  field_key: "",
  label: "",
  field_type: "text",
  is_required: false,
  help_text: "",
  options_text: "",
  file_types: "",
  max_files: 3,
  auto_select: false,
};

function FieldEditor({ version }) {
  const fieldsQuery = useFields(version.id);
  const createField = useCreateField();
  const deleteField = useDeleteField();
  const reorder = useReorderFields();
  const [form, setForm] = useState(EMPTY_FIELD_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [generalError, setGeneralError] = useState("");

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

  const sanitizeKey = (key) =>
    key
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9_]/g, "_")
      .replace(/_+/g, "_");

  const onCreate = async (event) => {
    event.preventDefault();
    setFieldErrors({});
    setGeneralError("");

    // Auto-sanitize field_key if user typed uppercase or spaces
    const effectiveKey = form.field_key
      ? sanitizeKey(form.field_key)
      : form.label
      ? sanitizeKey(form.label)
      : "";

    const candidate = { ...form, field_key: effectiveKey };
    const parsed = callFieldSchema.safeParse(candidate);

    if (!parsed.success) {
      const errors = {};
      parsed.error.issues.forEach((issue) => {
        const fieldName = issue.path[0] ?? "general";
        errors[fieldName] = issue.message;
      });
      setFieldErrors(errors);
      if (errors.general) setGeneralError(errors.general);
      return;
    }

    try {
      const wantsOptions = ["select", "radio", "checkbox"].includes(candidate.field_type);
      await createField.mutateAsync({
        template_version: version.id,
        field_key: candidate.field_key,
        label: candidate.label,
        field_type: candidate.field_type,
        is_required: candidate.is_required,
        help_text: candidate.help_text || undefined,
        options: wantsOptions
          ? candidate.options_text
              .split(",")
              .map((option) => option.trim())
              .filter(Boolean)
          : undefined,
        validation_rules: {
          ...(candidate.file_types ? { file_types: candidate.file_types } : {}),
          ...(candidate.field_type === "file" && candidate.max_files ? { max_files: Number(candidate.max_files) } : {}),
          ...(candidate.auto_select ? { auto_select: true } : {}),
        },
      });
      setForm(EMPTY_FIELD_FORM);
      setFieldErrors({});
      setGeneralError("");
    } catch (err) {
      if (err?.normalized?.fieldErrors) {
        const backendErrors = {};
        Object.entries(err.normalized.fieldErrors).forEach(([k, msgs]) => {
          backendErrors[k] = Array.isArray(msgs) ? msgs[0] : msgs;
        });
        setFieldErrors(backendErrors);
      } else {
        setGeneralError(err?.message ?? "Failed to create field.");
      }
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
            <FormField
              id="f_key"
              label="Key"
              required
              error={fieldErrors.field_key}
              help="Lowercase letters, digits and underscores."
            >
              <Input
                id="f_key"
                placeholder="e.g. company_name"
                className={fieldErrors.field_key ? "border-destructive" : ""}
                value={form.field_key}
                onChange={(e) => setForm({ ...form, field_key: e.target.value })}
              />
            </FormField>
            <FormField id="f_label" label="Label" required error={fieldErrors.label}>
              <Input
                id="f_label"
                placeholder="e.g. Company Name"
                className={fieldErrors.label ? "border-destructive" : ""}
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
              />
            </FormField>
            <FormField id="f_type" label="Type" error={fieldErrors.field_type}>
              <Select value={form.field_type} onValueChange={(value) => setForm({ ...form, field_type: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {FIELD_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>{type}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField id="f_options" label="Options (select/radio/checkbox)" error={fieldErrors.options_text}>
              <Input
                id="f_options"
                placeholder="a,b,c"
                className={fieldErrors.options_text ? "border-destructive" : ""}
                value={form.options_text}
                onChange={(e) => setForm({ ...form, options_text: e.target.value })}
                disabled={!["select", "radio", "checkbox"].includes(form.field_type)}
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
              {createField.isPending ? "Adding…" : "Add field"}
            </Button>
            <FormField id="f_file_types" label="File types (file only)" error={fieldErrors.file_types} help="e.g. pdf,docx,jpg">
              <Input id="f_file_types" placeholder="pdf,docx,jpg" value={form.file_types} onChange={(e) => setForm({ ...form, file_types: e.target.value })} disabled={form.field_type !== "file"} />
            </FormField>
            <FormField id="f_max_files" label="Max files" error={fieldErrors.max_files}>
              <Input id="f_max_files" type="number" min="1" max="10" value={form.max_files} onChange={(e) => setForm({ ...form, max_files: e.target.value })} disabled={form.field_type !== "file"} />
            </FormField>
            <label className="mt-6 flex items-center gap-2 text-sm md:col-span-2">
              <input type="checkbox" className="h-4 w-4" checked={form.auto_select} onChange={(e) => setForm({ ...form, auto_select: e.target.checked })} disabled={!["select", "radio", "checkbox"].includes(form.field_type)} />
              Auto-select first option
            </label>

            {generalError ? (
              <p role="alert" className="text-sm text-destructive md:col-span-6">
                {generalError}
              </p>
            ) : null}
          </form>
        ) : null}
      </CardContent>
    </Card>
  );
}

function FieldMappingEditor({ templateId }) {
  const mappingsQ = useFieldMappings(templateId);
  const create = useCreateFieldMapping();
  const del = useDeleteFieldMapping();
  const [form, setForm] = useState({ field_key: "", target_model: "Lead", target_field: "" });
  const onAdd = async (e) => {
    e.preventDefault();
    if (!form.field_key || !form.target_field) return;
    await create.mutateAsync({ template: templateId, field_key: form.field_key.toLowerCase().replace(/[^a-z0-9_]/g, "_"), target_model: form.target_model, target_field: form.target_field });
    setForm({ field_key: "", target_model: "Lead", target_field: "" });
  };
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Field → Lead/Customer Mapping (Admin)</CardTitle></CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-xs text-muted-foreground">Map template field_key to Lead/Customer field. e.g. <code>gst_number → Lead.metadata.gst_number</code> or <code>company_name → Lead.company_name</code>. On submit, values are upserted via <code>PATCH /leads/&#123;id&#125;/</code> semantics (fill-if-blank for direct columns).</p>
        {(mappingsQ.data ?? []).length === 0 ? <p className="text-xs text-muted-foreground">No mappings yet — defaults (name/email/phone/company) still apply.</p> : (
          <div className="flex flex-col gap-1">
            {(mappingsQ.data ?? []).map((m) => (
              <div key={m.id} className="flex items-center gap-2 rounded border px-2 py-1 text-xs">
                <span className="font-mono">{m.field_key}</span><span>→</span><Badge variant="outline">{m.target_model}.{m.target_field}</Badge>
                <Button size="sm" variant="ghost" className="ml-auto h-6 text-destructive" onClick={() => del.mutateAsync(m.id)}>Remove</Button>
              </div>
            ))}
          </div>
        )}
        <form onSubmit={onAdd} className="grid gap-2 md:grid-cols-4">
          <Input placeholder="field_key" value={form.field_key} onChange={(e) => setForm({ ...form, field_key: e.target.value })} />
          <Select value={form.target_model} onValueChange={(v) => setForm({ ...form, target_model: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="Lead">Lead</SelectItem><SelectItem value="Customer">Customer</SelectItem><SelectItem value="CustomerAccount">CustomerAccount</SelectItem></SelectContent></Select>
          <Input placeholder="target_field e.g. metadata.annual_revenue or company_name" value={form.target_field} onChange={(e) => setForm({ ...form, target_field: e.target.value })} />
          <Button type="submit" disabled={create.isPending}>Add mapping</Button>
        </form>
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
          <FieldMappingEditor templateId={template.id} />
          {selected ? <VersionAnalytics versionId={selected.id} /> : null}
        </>
      )}
    </div>
  );
}
