export const MEETING_TEMPLATE_MARKER = "__MEETING_TEMPLATE__";
export const meetingTemplateDescription = (type = "online") => `${MEETING_TEMPLATE_MARKER}:${type}`;
export const meetingTemplateType = (template) => template?.description?.split(":")[1] || "online";
