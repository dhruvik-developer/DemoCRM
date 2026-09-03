// Lead picker for forms that require a lead (Tasks, Activities contexts).
// Uses the real leads list when the caller has view_lead; otherwise falls
// back to manual UUID entry (no role currently grants both add_task and
// view_lead except Admin under G23 seeds, but this keeps it future-proof).

import { useState } from "react";
import { useLeads } from "../hooks";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function LeadSelect({ value, onChange, disabled }) {
  const [manualMode, setManualMode] = useState(false);
  const leadsQuery = useLeads({ page_size: 50 });
  const leads = leadsQuery.data?.results ?? [];
  const canListLeads = !leadsQuery.isError && leads.length > 0;

  if (manualMode || (!canListLeads && !leadsQuery.isLoading)) {
    return (
      <div className="flex flex-col gap-1">
        <Input
          placeholder="Lead UUID"
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
        />
        <button
          type="button"
          className="w-fit text-xs text-muted-foreground hover:underline"
          onClick={() => setManualMode(false)}
        >
          Try picking from the list instead
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger className="w-full">
          <SelectValue
            placeholder={leadsQuery.isLoading ? "Loading leads…" : "Select lead"}
          />
        </SelectTrigger>
        <SelectContent>
          {leads.map((lead) => (
            <SelectItem key={lead.id} value={String(lead.id)}>
              <span className="font-medium truncate">{lead.name || "Unnamed Lead"}</span>
              {lead.company_name || lead.email ? (
                <span className="text-xs text-muted-foreground ml-2 truncate">
                  ({lead.company_name || lead.email})
                </span>
              ) : null}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <button
        type="button"
        className="w-fit text-xs text-muted-foreground hover:underline"
        onClick={() => setManualMode(true)}
      >
        Enter a lead UUID manually
      </button>
    </div>
  );
}
