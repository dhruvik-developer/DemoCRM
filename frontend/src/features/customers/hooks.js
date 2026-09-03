// Customer queries. Smart lookup is enabled only when at least one search
// criterion is present; it is read-only so no invalidation is needed.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { customerKeys, leadKeys } from "@/api/queryKeys";
import { getApiErrorMessage } from "@/utils/errors";
import { getCustomer, getCustomerActivities, getCustomers, getPayments, recordCustomerPayment, smartLookup } from "./api";

export function useCustomers(filters) {
  return useQuery({
    queryKey: customerKeys.list(filters),
    queryFn: async () => {
      const data = await getCustomers(filters);
      if (Array.isArray(data)) {
        return { count: data.length, results: data };
      }
      return data;
    },
    placeholderData: (previous) => previous,
  });
}

export function useCustomer(customerId) {
  return useQuery({
    queryKey: customerKeys.detail(customerId),
    queryFn: () => getCustomer(customerId),
    enabled: Boolean(customerId),
  });
}

export function useCustomerActivities(customerId) {
  return useQuery({
    queryKey: [...customerKeys.activities(customerId), "list"],
    queryFn: () => getCustomerActivities(customerId),
    enabled: Boolean(customerId),
  });
}

export function useSmartLookup(params) {
  const hasCriteria = Object.values(params ?? {}).some(Boolean);
  return useQuery({
    queryKey: customerKeys.smartLookup(params),
    queryFn: () => smartLookup(params),
    enabled: hasCriteria,
    staleTime: 30000,
  });
}

export function usePayments(filters) {
  return useQuery({
    queryKey: customerKeys.payments(filters),
    queryFn: () => getPayments(filters),
    placeholderData: (previous) => previous,
  });
}

export function useRecordCustomerPayment(customerId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => recordCustomerPayment(customerId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: customerKeys.all });
      qc.invalidateQueries({ queryKey: leadKeys.all });
      qc.invalidateQueries({ queryKey: customerKeys.payments() });
      toast.success("Payment recorded.");
    },
    onError: (e) => toast.error(getApiErrorMessage(e)),
  });
}
