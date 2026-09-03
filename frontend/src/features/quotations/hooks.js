// Quotation queries + mutations. Accept/reject touch the Lead and Customer
// too (auto-convert / auto mark-lost), so those caches are invalidated.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { customerKeys, leadKeys, quotationKeys } from "@/api/queryKeys";
import { getApiErrorMessage } from "@/utils/errors";
import {
  acceptQuotation,
  approveQuotation,
  createQuotation,
  deleteQuotation,
  downloadQuotationPdf,
  getQuotation,
  getQuotations,
  rejectApproval,
  rejectQuotation,
  requestRevision,
  sendQuotation,
  sendQuotationEmail,
  submitQuotation,
  updateDraft,
} from "./api";

export function useQuotations(filters) {
  return useQuery({
    queryKey: quotationKeys.list(filters),
    queryFn: () => getQuotations(filters),
    placeholderData: (previous) => previous,
  });
}

export function useQuotation(quotationId) {
  return useQuery({
    queryKey: quotationKeys.detail(quotationId),
    queryFn: () => getQuotation(quotationId),
    enabled: Boolean(quotationId),
  });
}

function useInvalidateQuotations({ alsoLeadAndCustomer = false } = {}) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: quotationKeys.all });
    if (alsoLeadAndCustomer) {
      // Accept auto-converts the lead; reject marks it LOST.
      queryClient.invalidateQueries({ queryKey: leadKeys.all });
      queryClient.invalidateQueries({ queryKey: customerKeys.all });
    }
  };
}

export function useCreateQuotation() {
  const invalidate = useInvalidateQuotations({ alsoLeadAndCustomer: true });
  return useMutation({
    mutationFn: createQuotation,
    onSuccess: (quotation) => {
      invalidate();
      toast.success("Draft quotation created.");
      return quotation;
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useUpdateDraft(quotationId) {
  const invalidate = useInvalidateQuotations();
  return useMutation({
    mutationFn: (values) => updateDraft(quotationId, values),
    onSuccess: () => {
      invalidate();
      toast.success("Draft updated.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useSubmitQuotation(quotationId) {
  const invalidate = useInvalidateQuotations();
  return useMutation({
    mutationFn: () => submitQuotation(quotationId),
    onSuccess: (data) => {
      invalidate();
      toast.success(
        data?.quotation?.status === "APPROVED"
          ? "Submitted — auto-approved (no approval required for this stage)."
          : "Submitted for approval.",
      );
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useApproveQuotation(quotationId) {
  const invalidate = useInvalidateQuotations();
  return useMutation({
    mutationFn: () => approveQuotation(quotationId),
    onSuccess: () => {
      invalidate();
      toast.success("Quotation approved.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useRefuseApproval(quotationId) {
  const invalidate = useInvalidateQuotations();
  return useMutation({
    mutationFn: (reason) => rejectApproval(quotationId, reason),
    onSuccess: () => {
      invalidate();
      toast.success("Sent back to draft.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useSendQuotation(quotationId) {
  const invalidate = useInvalidateQuotations();
  return useMutation({
    mutationFn: () => sendQuotation(quotationId),
    onSuccess: () => {
      invalidate();
      toast.success("Quotation marked as sent.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useSendQuotationEmail(quotationId) {
  const invalidate = useInvalidateQuotations();
  return useMutation({
    mutationFn: (payload) => sendQuotationEmail(quotationId, payload),
    onSuccess: () => {
      invalidate();
      toast.success("Email sent.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useRequestRevision(quotationId) {
  const invalidate = useInvalidateQuotations();
  return useMutation({
    mutationFn: (values) => requestRevision(quotationId, values),
    onSuccess: () => {
      invalidate();
      toast.success("New draft revision created.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useAcceptQuotation(quotationId) {
  const invalidate = useInvalidateQuotations({ alsoLeadAndCustomer: true });
  return useMutation({
    mutationFn: () => acceptQuotation(quotationId),
    onSuccess: () => {
      invalidate();
      toast.success("Quotation accepted — the lead was converted to a customer.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useRefuseQuotation(quotationId) {
  const invalidate = useInvalidateQuotations({ alsoLeadAndCustomer: true });
  return useMutation({
    mutationFn: (reason) => rejectQuotation(quotationId, reason),
    onSuccess: () => {
      invalidate();
      toast.success("Quotation rejected — the lead was marked lost.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export function useDeleteQuotation() {
  const invalidate = useInvalidateQuotations();
  return useMutation({
    mutationFn: (quotationId) => deleteQuotation(quotationId),
    onSuccess: () => {
      invalidate();
      toast.success("Draft quotation deleted.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}

export { downloadQuotationPdf };
