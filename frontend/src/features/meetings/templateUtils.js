export const MEETING_TEMPLATE_MARKER = "__MEETING_TEMPLATE__";
export const meetingTemplateDescription = (type = "online") => `${MEETING_TEMPLATE_MARKER}:${type}`;
export const meetingTemplateType = (template) => template?.description?.split(":")[1] || "online";

const approvalBody = `Hello {{manager_name}},

{{employee_name}} has requested a meeting.

Meeting: {{meeting_title}}
Customer: {{customer_name}}
Date: {{meeting_date}}
Time: {{start_time}} - {{end_time}}
Link: {{meeting_link}}
Location: {{location}}

Please approve or reject this meeting.

Regards,
CRM Team`;

const scheduledBody = `Hello,

The meeting has been approved and scheduled successfully.

Meeting Title: {{meeting_title}}
Customer: {{customer_name}}
Date: {{meeting_date}}
Time: {{start_time}} - {{end_time}}
Google Meet Link: {{meeting_link}}
Location: {{location}}
Description: {{description}}

Please be ready at the scheduled time.

Regards,
CRM System`;

const rescheduleBody = `Hello {{manager_name}},

{{employee_name}} has rescheduled the meeting.

Meeting: {{meeting_title}}
New Date: {{meeting_date}}
New Time: {{start_time}} - {{end_time}}

Please approve or reject the meeting again.

Regards,
CRM Team`;

export function defaultMeetingEmailConfiguration(type = "online") {
  if (type === "reschedule") {
    return { rescheduled: { subject: "Meeting Rescheduled: {{meeting_title}}", body: rescheduleBody } };
  }
  return {
    approval_request: { subject: "Meeting Approval Required: {{meeting_title}}", body: approvalBody },
    scheduled: { subject: "Meeting Scheduled: {{meeting_title}}", body: scheduledBody },
  };
}
