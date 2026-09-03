import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";

import { useCreateCallTemplate } from "@/features/callforms/hooks";
import FormField from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { defaultMeetingEmailConfiguration, meetingTemplateDescription } from "../templateUtils";

export default function MeetingTemplateCreatePage() {
  const navigate = useNavigate();
  const createTemplate = useCreateCallTemplate();

  const form = useForm({
    defaultValues: { name: "", template_type: "online" },
  });

  const onSubmit = async (values) => {
    const template = await createTemplate.mutateAsync({
      name: values.name,
      description: meetingTemplateDescription(values.template_type),
      email_configuration: defaultMeetingEmailConfiguration(values.template_type),
      initial_fields: [],
    });
    navigate(`/meeting-templates/${template.id}`);
  };

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">New meeting template</h1>
        <Button variant="ghost" asChild>
          <Link to="/meeting-templates">Cancel</Link>
        </Button>
      </div>

      <p className="text-sm text-muted-foreground">
        Create a meeting template, then add fields to its form.
      </p>

      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <FormField id="meeting_template_name" label="Template name" required>
          <Input
            id="meeting_template_name"
            {...form.register("name", { required: "Template name is required." })}
          />
        </FormField>

        <FormField id="meeting_template_type" label="Meeting workflow">
          <Select
            value={form.watch("template_type")}
            onValueChange={(value) => form.setValue("template_type", value)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="online">Online meeting</SelectItem>
              <SelectItem value="offline">Offline meeting</SelectItem>
              <SelectItem value="reschedule">Reschedule request</SelectItem>
            </SelectContent>
          </Select>
        </FormField>

        <Button type="submit" disabled={createTemplate.isPending} className="self-start">
          {createTemplate.isPending ? "Creating…" : "Create template"}
        </Button>
      </form>
    </div>
  );
}
