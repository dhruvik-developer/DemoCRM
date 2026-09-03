// Template detail: versions + primary selection + per-version field editor
// + submission analytics. A version with submissions is LOCKED — the editor
// is disabled with a banner (the backend 400s mutations anyway).

import { useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
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
  useUpdateCallTemplate,
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
import { Textarea } from "@/components/ui/textarea";
import { defaultMeetingEmailConfiguration, meetingTemplateType } from "@/features/meetings/templateUtils";
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

const EMAIL_EVENT_LABELS = {
  approval_request: "Approval request email",
  scheduled: "Approved / scheduled email",
  rescheduled: "Reschedule approval email",
};

function MeetingEmailEditor({ template }) {
  const updateTemplate = useUpdateCallTemplate();
  const workflow = meetingTemplateType(template);
  const [configuration, setConfiguration] = useState(() =>
    Object.keys(template.email_configuration || {}).length
      ? template.email_configuration
      : defaultMeetingEmailConfiguration(workflow),
  );
  const setEventValue = (eventName, key, value) => setConfiguration((current) => ({
    ...current,
    [eventName]: { ...(current[eventName] || {}), [key]: value },
  }));

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Automatic email templates</CardTitle></CardHeader>
      <CardContent className="space-y-5">
        <p className="text-xs text-muted-foreground">
          These emails are sent automatically by the meeting workflow. Dynamic variables use double braces, for example {"{{meeting_title}}"}.
        </p>
        {Object.entries(configuration).map(([eventName, email]) => (
          <div key={eventName} className="space-y-3 rounded-lg border p-4">
            <h3 className="font-medium">{EMAIL_EVENT_LABELS[eventName] || eventName}</h3>
            <FormField id={`${eventName}_subject`} label="Email subject">
              <Input value={email.subject || ""} onChange={(event) => setEventValue(eventName, "subject", event.target.value)} />
            </FormField>
            <FormField id={`${eventName}_body`} label="Email body">
              <Textarea rows={12} value={email.body || ""} onChange={(event) => setEventValue(eventName, "body", event.target.value)} />
            </FormField>
          </div>
        ))}
        <div className="rounded-md bg-muted p-3 text-xs text-muted-foreground">
          Available variables: meeting_title, customer_name, meeting_date, start_time, end_time, meeting_link, location, description, employee_name, manager_name, and every custom field key added below.
        </div>
        <Button disabled={updateTemplate.isPending} onClick={() => updateTemplate.mutateAsync({ id: template.id, email_configuration: configuration })}>
          {updateTemplate.isPending ? "Saving…" : "Save email templates"}
        </Button>
      </CardContent>
    </Card>
  );
}

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
            <p className="text-sm text-muted-foreground">No fields yet. Add your first field below.</p>
          ) : null}
          {fields.map((field, index) => {
            const isChoice = ["select", "radio", "checkbox"].includes(field.field_type);
            const isFile = field.field_type === "file";
            return (
              <div key={field.id} className="flex flex-col gap-1.5 rounded-lg border bg-card p-3 text-sm shadow-sm">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-muted-foreground">{field.field_key}</span>
                  <span className="font-medium">{field.label}</span>
                  <Badge variant="outline" className="capitalize">{field.field_type}</Badge>
                  {field.is_required ? <Badge variant="secondary">required</Badge> : <Badge variant="outline" className="text-muted-foreground">optional</Badge>}
                  <div className="ml-auto flex gap-1">
                    <Button variant="ghost" size="sm" disabled={locked || index === 0} onClick={() => move(index, -1)}>↑</Button>
                    <Button variant="ghost" size="sm" disabled={locked || index === fields.length - 1} onClick={() => move(index, 1)}>↓</Button>
                    {!locked ? (
                      <Button variant="ghost" size="sm" className="text-destructive" onClick={() => deleteField.mutateAsync(field.id)}>✕</Button>
                    ) : null}
                  </div>
                </div>
                {(isChoice || isFile) ? (
                  <div className="flex flex-wrap items-center gap-1.5 pl-0.5">
                    {isChoice && field.options?.length ? (
                      <span className="inline-flex flex-wrap gap-1">
                        <span className="text-xs text-muted-foreground">Options:</span>
                        {field.options.map((opt) => <Badge key={opt} variant="secondary" className="text-[11px] font-normal">{opt}</Badge>)}
                        {field.validation_rules?.auto_select ? <Badge variant="outline" className="text-[11px]">auto-select first</Badge> : null}
                      </span>
                    ) : null}
                    {isFile ? (
                      <>
                        {field.validation_rules?.file_types ? <Badge variant="outline" className="text-[11px]">types: {field.validation_rules.file_types}</Badge> : <Badge variant="outline" className="text-[11px]">any file</Badge>}
                        <Badge variant="secondary" className="text-[11px]">max {field.validation_rules?.max_files ?? 3} files</Badge>
                      </>
                    ) : null}
                  </div>
                ) : null}
                {field.help_text ? <p className="text-xs text-muted-foreground">{field.help_text}</p> : null}
              </div>
            );
          })}
        </div>

        {!locked ? (
          <form onSubmit={onCreate} className="flex flex-col gap-4 rounded-lg border bg-muted/20 p-4">
            <div className="grid gap-3 md:grid-cols-3">
              <FormField id="f_key" label="Key" required error={fieldErrors.field_key} help="Lowercase letters, digits and underscores. Auto-sanitized from Label if empty.">
                <Input id="f_key" placeholder="e.g. company_name" className={fieldErrors.field_key ? "border-destructive" : ""} value={form.field_key} onChange={(e) => setForm({ ...form, field_key: e.target.value })} />
              </FormField>
              <FormField id="f_label" label="Label" required error={fieldErrors.label} help="Second column — what the agent sees. e.g. 'Company Name', 'GST No.'">
                <Input id="f_label" placeholder="e.g. Company Name" className={fieldErrors.label ? "border-destructive" : ""} value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
              </FormField>
              <FormField id="f_type" label="Type" error={fieldErrors.field_type} help="Controls widget + validation. File shows File types/Max files; Select/Radio/Checkbox shows Options.">
                <Select value={form.field_type} onValueChange={(value) => setForm({ ...form, field_type: value })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {FIELD_TYPES.map((type) => (
                      <SelectItem key={type} value={type} className="capitalize">{type}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
            </div>

            {(() => {
              const isChoice = ["select", "radio", "checkbox"].includes(form.field_type);
              const isFile = form.field_type === "file";
              const optionsList = form.options_text ? form.options_text.split(",").map((s) => s.trim()).filter(Boolean) : [];
              const fileList = form.file_types ? form.file_types.split(",").map((s) => s.trim()).filter(Boolean) : [];
              const addOpt = () => { const v = (form._optInput ?? "").trim(); if (!v) return; if (optionsList.includes(v)) return; setForm((p) => ({ ...p, options_text: [...optionsList, v].join(","), _optInput: "" })); };
              const addFile = () => { const v = (form._fileInput ?? "").trim().toLowerCase().replace(".", ""); if (!v) return; if (fileList.includes(v)) return; setForm((p) => ({ ...p, file_types: [...fileList, v].join(","), _fileInput: "" })); };
              if (isChoice) {
                return (
                  <div className="flex flex-col gap-3 rounded-md border border-dashed bg-card p-3 animate-in fade-in">
                    <FormField id="f_options" label="Options (select / radio / checkbox only)" required error={fieldErrors.options_text} help="Type option → Add. Chips appear below. Click ✕ to edit/delete. Required for these 3 types.">
                      <div className="flex gap-2">
                        <Input id="f_options" placeholder="e.g. High" value={form._optInput ?? ""} onChange={(e) => setForm((p) => ({ ...p, _optInput: e.target.value }))} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addOpt(); } }} />
                        <Button type="button" variant="outline" onClick={addOpt}>Add</Button>
                      </div>
                    </FormField>
                    {optionsList.length ? (
                      <div className="flex flex-wrap gap-1.5">
                        {optionsList.map((opt) => (
                          <Badge key={opt} variant="secondary" className="gap-1 pr-1 text-xs font-normal">
                            {opt}
                            <button type="button" aria-label={`Remove ${opt}`} className="ml-1 rounded-full hover:bg-black/10 px-1" onClick={() => setForm((p) => ({ ...p, options_text: optionsList.filter((o) => o !== opt).join(",") }))}>✕</button>
                          </Badge>
                        ))}
                      </div>
                    ) : <p className="text-xs text-muted-foreground">No options yet. Add at least one above. Stored as comma string for API.</p>}
                    <div className="flex flex-wrap items-center gap-4 pt-1">
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" className="h-4 w-4" checked={form.auto_select} onChange={(e) => setForm({ ...form, auto_select: e.target.checked })} />
                        Auto-select first option
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" className="h-4 w-4" checked={form.is_required} onChange={(e) => setForm({ ...form, is_required: e.target.checked })} />
                        Required
                      </label>
                      <span className="ml-auto text-xs text-muted-foreground hidden sm:inline">Hidden when Type ≠ select/radio/checkbox</span>
                    </div>
                  </div>
                );
              }
              if (isFile) {
                return (
                  <div className="flex flex-col gap-3 rounded-md border border-dashed bg-card p-3 animate-in fade-in">
                    <div className="grid gap-3 md:grid-cols-2">
                      <FormField id="f_file_types" label="File types (file only)" error={fieldErrors.file_types} help="Type ext without dot → Add. e.g. pdf,docx,jpg. Chips appear.">
                        <div className="flex gap-2">
                          <Input id="f_file_types" placeholder="e.g. pdf" value={form._fileInput ?? ""} onChange={(e) => setForm((p) => ({ ...p, _fileInput: e.target.value }))} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addFile(); } }} />
                          <Button type="button" variant="outline" onClick={addFile}>Add</Button>
                        </div>
                        {fileList.length ? (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {fileList.map((ext) => (
                              <Badge key={ext} variant="outline" className="gap-1 pr-1 text-xs font-normal">.{ext}
                                <button type="button" aria-label={`Remove ${ext}`} className="ml-1 rounded-full hover:bg-black/10 px-1" onClick={() => setForm((p) => ({ ...p, file_types: fileList.filter((o) => o !== ext).join(",") }))}>✕</button>
                              </Badge>
                            ))}
                          </div>
                        ) : null}
                      </FormField>
                      <FormField id="f_max_files" label="Max files" error={fieldErrors.max_files} help="1–10. Default 3. Shown only for file type.">
                        <Input id="f_max_files" type="number" min="1" max="10" value={form.max_files} onChange={(e) => setForm({ ...form, max_files: e.target.value })} />
                      </FormField>
                    </div>
                    <label className="flex items-center gap-2 text-sm">
                      <input type="checkbox" className="h-4 w-4" checked={form.is_required} onChange={(e) => setForm({ ...form, is_required: e.target.checked })} />
                      Required
                    </label>
                  </div>
                );
              }
              return (
                <div className="flex items-center gap-4 rounded-md border border-dashed px-3 py-3">
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" className="h-4 w-4" checked={form.is_required} onChange={(e) => setForm({ ...form, is_required: e.target.checked })} />
                    Required
                  </label>
                  <span className="text-xs text-muted-foreground">No extra settings for {form.field_type} — switch Type to select/radio/checkbox for Options, or file for File types.</span>
                </div>
              );
            })()}

            <div className="flex justify-end">
              <Button type="submit" disabled={createField.isPending} className="min-w-28">
                {createField.isPending ? "Adding…" : "Add field"}
              </Button>
            </div>
            {generalError ? <p role="alert" className="text-sm text-destructive">{generalError}</p> : null}
          </form>
        ) : null}
      </CardContent>
    </Card>
  );
}

function MeetingCustomFieldsEditor({ version }) {
  const fieldsQuery = useFields(version.id);
  const createField = useCreateField();
  const deleteField = useDeleteField();
  const [draft, setDraft] = useState({ label: "", field_type: "text", is_required: false, options: "" });
  const fields = fieldsQuery.data ?? [];
  const addField = async () => {
    const label = draft.label.trim();
    if (!label) return;
    const fieldKey = label.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
    await createField.mutateAsync({
      template_version: version.id,
      field_key: fieldKey,
      label,
      field_type: draft.field_type,
      is_required: draft.is_required,
      options: ["select", "radio", "checkbox"].includes(draft.field_type)
        ? draft.options.split(",").map((value) => value.trim()).filter(Boolean)
        : [],
    });
    setDraft({ label: "", field_type: "text", is_required: false, options: "" });
  };

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Custom Fields</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground">Add extra fields to this meeting form whenever you need them.</p>
        {fields.length ? <div className="space-y-2">{fields.map((field) => (
          <div key={field.id} className="flex items-center gap-3 rounded-lg border px-3 py-2">
            <span className="font-medium">{field.label}</span>
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs capitalize">{field.field_type}</span>
            {field.is_required ? <span className="text-xs text-muted-foreground">Required</span> : null}
            <Button type="button" variant="ghost" size="sm" className="ml-auto text-destructive" onClick={() => deleteField.mutateAsync(field.id)}>Remove</Button>
          </div>
        ))}</div> : <p className="rounded-lg border border-dashed p-5 text-center text-sm text-muted-foreground">No custom fields added yet.</p>}

        <div className="grid items-end gap-3 rounded-lg border bg-muted/15 p-4 md:grid-cols-2">
          <FormField id="meeting_field_name" label="Field name"><Input value={draft.label} placeholder="e.g. Agenda or Contact person" onChange={(event) => setDraft({ ...draft, label: event.target.value })} /></FormField>
          <FormField id="meeting_field_type" label="Field type"><Select value={draft.field_type} onValueChange={(value) => setDraft({ ...draft, field_type: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["text", "textarea", "number", "date", "time", "boolean", "select", "radio", "checkbox"].map((type) => <SelectItem key={type} value={type} className="capitalize">{type}</SelectItem>)}</SelectContent></Select></FormField>
          {["select", "radio", "checkbox"].includes(draft.field_type) ? <FormField id="meeting_field_options" label="Options"><Input value={draft.options} placeholder="Option one, Option two" onChange={(event) => setDraft({ ...draft, options: event.target.value })} /></FormField> : null}
          <label className="flex h-9 items-center gap-2 text-sm"><input type="checkbox" checked={draft.is_required} onChange={(event) => setDraft({ ...draft, is_required: event.target.checked })} /> Required field</label>
          <Button type="button" variant="outline" disabled={!draft.label.trim() || createField.isPending} onClick={addField}>+ Add field</Button>
        </div>
      </CardContent>
    </Card>
  );
}

function MeetingFormStructure({ version, template }) {
  const fieldsQuery = useFields(version.id);
  const updateTemplate = useUpdateCallTemplate();
  const deleteField = useDeleteField();
  const [values, setValues] = useState(template.email_configuration?.form_values || {});
  const [hiddenFields, setHiddenFields] = useState(template.email_configuration?.hidden_fields || []);
  const standardRows = [
    ["Title", "meeting_title", "text"],
    ["Meeting Venue", "meeting_type", "text"],
    ["Location", "location", "text"],
    ["All day", "all_day", "checkbox"],
    ["From", "from", "datetime-local"],
    ["To", "to", "datetime-local"],
    ["Host", "manager_name", "text"],
    ["Participants", "participants", "text"],
    ["Meeting Link", "meeting_link", "url"],
    ["Details/Description", "description", "textarea"],
  ];
  const customRows = (fieldsQuery.data ?? []).map((field) => [
    field.label,
    field.field_key,
    field.field_type,
  ]);
  const setValue = (key, value) => setValues((current) => ({ ...current, [key]: value }));
  const save = () => updateTemplate.mutateAsync({ id: template.id, email_configuration: { ...(template.email_configuration || {}), form_values: values, hidden_fields: hiddenFields } });
  const visibleRows = [...standardRows, ...customRows].filter(([, key]) => !hiddenFields.includes(key));
  const customKeys = new Set((fieldsQuery.data ?? []).map((field) => field.field_key));
  const removeRow = async (key) => {
    if (customKeys.has(key)) {
      const field = (fieldsQuery.data ?? []).find((item) => item.field_key === key);
      if (field) await deleteField.mutateAsync(field.id);
      return;
    }
    setHiddenFields((current) => [...new Set([...current, key])]);
  };

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Meeting form structure</CardTitle></CardHeader>
      <CardContent>
        <p className="mb-4 text-xs text-muted-foreground">Type directly in the Value column. Custom fields added below automatically appear here.</p>
        <div className="overflow-hidden rounded-lg border">
          <div className="grid grid-cols-[minmax(140px,0.35fr)_1fr_auto] gap-3 border-b bg-muted/40 px-4 py-3 text-sm font-semibold">
            <span>Form Field</span><span>Value</span><span>Action</span>
          </div>
          {visibleRows.map(([label, key, type]) => (
            <div key={key} className="grid grid-cols-[minmax(140px,0.35fr)_1fr_auto] items-center gap-3 border-b px-4 py-2 text-sm last:border-b-0">
              <strong>{label}</strong>
              {type === "checkbox" || type === "boolean" ? <label className="flex items-center gap-2"><input type="checkbox" checked={Boolean(values[key])} onChange={(event) => setValue(key, event.target.checked)} /> {values[key] ? "Yes" : "No"}</label> : type === "textarea" ? <Textarea rows={3} value={values[key] || ""} placeholder={`Enter ${label.toLowerCase()}`} onChange={(event) => setValue(key, event.target.value)} /> : <Input type={["date", "time", "number", "url", "datetime-local"].includes(type) ? type : "text"} value={values[key] || ""} placeholder={`Enter ${label.toLowerCase()}`} onChange={(event) => setValue(key, event.target.value)} />}
              <Button type="button" variant="ghost" size="sm" className="text-destructive" disabled={deleteField.isPending} onClick={() => removeRow(key)}>Delete</Button>
            </div>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button disabled={updateTemplate.isPending} onClick={save}>{updateTemplate.isPending ? "Saving…" : "Save form values"}</Button>
          {hiddenFields.length ? <Button type="button" variant="outline" onClick={() => setHiddenFields([])}>Restore deleted standard rows</Button> : null}
        </div>
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
    <Card className="border-dashed">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Field → Lead / Customer Mapping (Admin)</CardTitle>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Second section — connect a template <code className="bg-muted px-1 rounded">field_key</code> (column 1) to a real record field (columns 2 + 3). Column 2 = <b>Target model</b> (where to store), Column 3 = <b>Target field</b> (which column). Examples: <code>gst_number → Lead.metadata.gst_number</code> (goes to <code>Lead.metadata</code>), <code>company_name → Lead.company_name</code> (direct column, fill-if-blank), <code>annual_revenue → Lead.metadata.annual_revenue</code>. On submit the value is upserted with <code>PATCH /leads/&#123;id&#125;/</code> semantics.
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {(mappingsQ.data ?? []).length === 0 ? (
          <p className="rounded-md border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">No mappings yet — defaults still apply: <code>name/full_name → Lead.name</code>, <code>email → Lead.email</code>, <code>phone/mobile → Lead.phone</code>, <code>company → Lead.company_name</code>, rest → <code>Lead.metadata</code>.</p>
        ) : (
          <>
            <div className="hidden md:grid grid-cols-[1.2fr_0.8fr_1.4fr_auto] gap-2 px-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              <span>1. field_key (template)</span><span>2. Target model</span><span>3. Target field</span><span></span>
            </div>
            <div className="flex flex-col gap-1.5">
              {(mappingsQ.data ?? []).map((m) => (
                <div key={m.id} className="grid items-center gap-2 rounded-md border bg-card px-2 py-2 text-xs md:grid-cols-[1.2fr_0.8fr_1.4fr_auto]">
                  <span className="font-mono font-medium">{m.field_key}</span>
                  <Badge variant="secondary" className="w-fit text-[11px]">{m.target_model}</Badge>
                  <span className="font-mono text-muted-foreground">{m.target_field}</span>
                  <Button size="sm" variant="ghost" className="h-7 text-destructive justify-self-end" onClick={() => del.mutateAsync(m.id)}>Remove</Button>
                </div>
              ))}
            </div>
          </>
        )}
        <form onSubmit={onAdd} className="grid gap-2 md:grid-cols-[1.2fr_0.8fr_1.4fr_auto] items-end rounded-lg border bg-muted/20 p-3">
          <FormField id="map_key" label="1. field_key" help="Must match a field in this template.">
            <Input id="map_key" placeholder="e.g. gst_number" value={form.field_key} onChange={(e) => setForm({ ...form, field_key: e.target.value })} />
          </FormField>
          <FormField id="map_model" label="2. Target model" help="Where to store.">
            <Select value={form.target_model} onValueChange={(v) => setForm({ ...form, target_model: v })}><SelectTrigger id="map_model"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="Lead">Lead</SelectItem><SelectItem value="Customer">Customer</SelectItem><SelectItem value="CustomerAccount">CustomerAccount</SelectItem></SelectContent></Select>
          </FormField>
          <FormField id="map_field" label="3. Target field" help="e.g. company_name or metadata.gst_number">
            <Input id="map_field" placeholder="e.g. metadata.annual_revenue" value={form.target_field} onChange={(e) => setForm({ ...form, target_field: e.target.value })} />
          </FormField>
          <Button type="submit" disabled={create.isPending || !form.field_key || !form.target_field} className="h-9">Add mapping</Button>
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
  const location = useLocation();
  const isMeetingTemplate = location.pathname.startsWith("/meeting-templates/");
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
          {!isMeetingTemplate ? <Button
            variant="outline"
            size="sm"
            disabled={createVersion.isPending}
            onClick={() => createVersion.mutateAsync({ templateId: template.id, version_label: "" })}
          >
            New version
          </Button> : null}
          {selected && !isMeetingTemplate ? (
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
            <Link to={isMeetingTemplate ? "/meeting-templates" : "/callforms"}>
              ← Templates
            </Link>
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
          {isMeetingTemplate ? (
            selected ? <MeetingFormStructure version={selected} template={template} /> : null
          ) : null}
          {!isMeetingTemplate ? <div className="flex flex-wrap items-center gap-2">
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
          </div> : null}

          {selected ? (isMeetingTemplate ? <MeetingCustomFieldsEditor key={selected.id} version={selected} /> : <FieldEditor key={selected.id} version={selected} />) : null}
          {!isMeetingTemplate ? <FieldMappingEditor templateId={template.id} /> : null}
          {selected && !isMeetingTemplate ? <VersionAnalytics versionId={selected.id} /> : null}
        </>
      )}
    </div>
  );
}
