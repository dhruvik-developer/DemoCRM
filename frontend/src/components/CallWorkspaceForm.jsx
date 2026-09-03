import { useState } from "react";

export const FORM_FIELDS = [
  {
    id: "callOutcome",
    label: "Call Outcome",
    type: "select",
    required: true,
    options: [
      "Connected - Interested",
      "Connected - Not Interested",
      "No Answer",
      "Call Back Later",
      "Wrong Number",
    ],
  },
  {
    id: "clientFeedback",
    label: "Client Feedback & Requirements",
    type: "textarea",
    showIf: {
      field: "callOutcome",
      values: ["Connected - Interested", "Connected - Not Interested"],
    },
  },
  {
    id: "proposedDealValue",
    label: "Proposed Deal Value / Quotation Amount",
    type: "number",
    showIf: { field: "callOutcome", value: "Connected - Interested" },
  },
  {
    id: "nextStepDate",
    label: "Agreed Next Step / Meeting Date",
    type: "date",
    showIf: {
      field: "callOutcome",
      values: ["Connected - Interested", "Call Back Later"],
    },
  },
];

const isVisible = (field, values) => {
  if (!field.showIf) return true;
  const currentValue = values[field.showIf.field];
  return field.showIf.values
    ? field.showIf.values.includes(currentValue)
    : currentValue === field.showIf.value;
};

function FieldControl({ field, value, error, onChange }) {
  const classes = `w-full rounded-md border bg-black px-3 py-2 text-sm text-white outline-none placeholder:text-gray-500 focus:border-blue-600 focus:ring-1 focus:ring-blue-600 ${error ? "border-red-500" : "border-gray-700"}`;

  if (field.type === "textarea") {
    return <textarea rows={3} className={classes} value={value} onChange={(event) => onChange(event.target.value)} />;
  }
  if (field.type === "select") {
    return (
      <select className={classes} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Select option...</option>
        {field.options?.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    );
  }
  return <input className={classes} type={field.type} value={value} onChange={(event) => onChange(event.target.value)} />;
}

export default function CallWorkspaceForm({
  lead = {},
  stage = "New",
  nextStage = "Contacted",
  pipeline = "Sales Pipeline",
  initialValues = {},
  onSaveDraft = () => {},
  onCompleteTask = () => {},
  onSubmitAndMove = () => {},
}) {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});

  const visibleFields = FORM_FIELDS.filter((field) => isVisible(field, values));
  const updateValue = (fieldId, value) => {
    setValues((current) => ({ ...current, [fieldId]: value }));
    setErrors((current) => {
      if (!current[fieldId]) return current;
      const next = { ...current };
      delete next[fieldId];
      return next;
    });
  };
  const validate = () => {
    const nextErrors = {};
    visibleFields.forEach((field) => {
      if (field.required && !String(values[field.id] ?? "").trim()) {
        nextErrors[field.id] = `${field.label} is required.`;
      }
    });
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  return (
    <section className="rounded-xl border border-gray-800 bg-black p-6 text-white">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><h2 className="text-lg font-semibold">Call Workspace — {lead.name || "Lead"}</h2><p className="text-sm text-gray-400">Active Call Form Steps & Lead Information for live data entry.</p></div>
        <span className="rounded-full bg-blue-600 px-3 py-1 text-xs font-semibold">Current Stage: {stage}</span>
      </div>

      <div className="my-6 grid gap-4 md:grid-cols-4">
        {[["Phone", lead.phone], ["Email", lead.email], ["Company", lead.company], ["Pipeline / Stage", `${pipeline} / ${stage}`]].map(([label, content]) => <div key={label}><p className="text-xs uppercase text-gray-500">{label}</p><p className="mt-1 text-sm font-medium">{content || "—"}</p></div>)}
      </div>

      <div className="mb-4 flex items-center justify-between"><h3 className="font-semibold">Call Form Steps — {stage}</h3><span className="text-xs text-gray-400">Next Step: {nextStage}</span></div>
      <div className="mb-3 flex justify-between text-xs uppercase text-gray-500"><span>Form Fields Workflow</span><span>{visibleFields.length} fields</span></div>

      <div className="space-y-4">
        {visibleFields.map((field, index) => (
          <div key={field.id}>
            <div className="mb-1 flex justify-between gap-2"><label htmlFor={field.id} className="text-sm font-medium">{field.label}{field.required ? <span className="text-red-500"> *</span> : null}</label><span className="text-xs text-gray-500">Step {index + 1} of {visibleFields.length}</span></div>
            <FieldControl field={field} value={values[field.id] ?? ""} error={errors[field.id]} onChange={(value) => updateValue(field.id, value)} />
            {errors[field.id] ? <p className="mt-1 text-xs text-red-500">{errors[field.id]}</p> : null}
          </div>
        ))}
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-gray-800 pt-4">
        <button type="button" className="rounded-md border border-gray-700 px-4 py-2 text-sm hover:bg-gray-900" onClick={() => onSaveDraft(values)}>Save Form Answers</button>
        <div className="flex flex-wrap gap-3">
          <button type="button" className="rounded-md border border-gray-700 px-4 py-2 text-sm hover:bg-gray-900" onClick={() => validate() && onCompleteTask(values)}>Complete Task</button>
          <button type="button" className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold hover:bg-blue-700" onClick={() => validate() && onSubmitAndMove(values)}>Submit & Move to {nextStage} →</button>
        </div>
      </div>
    </section>
  );
}
