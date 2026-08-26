// Quotations API — endpoints verified in frontend/docs/API_CONTRACT.md.
// Status transitions are enforced server-side; the UI mirrors them as buttons.

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function getQuotations(filters) {
  const { data } = await apiClient.get(endpoints.crm.quotations, {
    params: filters,
  });
  return data;
}

export async function getQuotation(quotationId) {
  const { data } = await apiClient.get(endpoints.crm.quotationDetail(quotationId));
  return data;
}

export async function createQuotation(values) {
  const { data } = await apiClient.post(endpoints.crm.quotations, values);
  return data;
}

export async function updateDraft(quotationId, values) {
  const { data } = await apiClient.patch(
    endpoints.crm.quotationUpdateDraft(quotationId),
    values,
  );
  return data;
}

export async function submitQuotation(quotationId) {
  const { data } = await apiClient.post(endpoints.crm.quotationSubmit(quotationId));
  return data;
}

export async function approveQuotation(quotationId) {
  const { data } = await apiClient.post(endpoints.crm.quotationApprove(quotationId));
  return data;
}

export async function rejectApproval(quotationId, reason) {
  const { data } = await apiClient.post(
    endpoints.crm.quotationRejectApproval(quotationId),
    reason ? { reason } : {},
  );
  return data;
}

export async function sendQuotation(quotationId) {
  const { data } = await apiClient.post(endpoints.crm.quotationSend(quotationId));
  return data;
}

export async function sendQuotationEmail(quotationId, payload) {
  const { data } = await apiClient.post(
    endpoints.crm.quotationSendEmail(quotationId),
    payload,
  );
  return data;
}

export async function requestRevision(quotationId, values) {
  const { data } = await apiClient.post(
    endpoints.crm.quotationRevision(quotationId),
    values ?? {},
  );
  return data;
}

/** Accepting auto-converts the lead into a Customer server-side. */
export async function acceptQuotation(quotationId) {
  const { data } = await apiClient.post(endpoints.crm.quotationAccept(quotationId));
  return data;
}

export async function rejectQuotation(quotationId, rejectionReason) {
  const { data } = await apiClient.post(endpoints.crm.quotationReject(quotationId), {
    rejection_reason: rejectionReason,
  });
  return data;
}

/**
 * PDF requires the Authorization header, so we fetch a blob instead of a
 * plain <a href>. Blocked by the backend for DRAFT/PENDING versions.
 */
export async function downloadQuotationPdf(quotationId, versionNumber) {
  const response = await apiClient.get(endpoints.crm.quotationPdf(quotationId), {
    params: versionNumber ? { version: versionNumber } : {},
    responseType: "blob",
  });

  const disposition = response.headers["content-disposition"] ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/);
  const filename =
    match?.[1] ?? `quotation-${quotationId.slice(0, 8)}${versionNumber ? `-v${versionNumber}` : ""}.pdf`;

  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
