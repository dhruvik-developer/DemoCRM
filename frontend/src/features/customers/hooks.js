// Customer queries. Smart lookup is enabled only when at least one search
// criterion is present; it is read-only so no invalidation is needed.

import { useQuery } from "@tanstack/react-query";
import { customerKeys } from "@/api/queryKeys";
import { getCustomer, getCustomerActivities, getCustomers, smartLookup } from "./api";

export function useCustomers(filters) {
  return useQuery({
    queryKey: customerKeys.list(filters),
    queryFn: () => getCustomers(filters),
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
