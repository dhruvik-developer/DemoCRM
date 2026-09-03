// Customers API — endpoints verified in frontend/docs/API_CONTRACT.md.
// CustomerSerializer exposes: id, lead, name, email, phone, company_name,
// created_at, updated_at. Smart lookup returns a composite envelope.

import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";

export async function getCustomers(filters) {
  const { data } = await apiClient.get(endpoints.crm.customers, { params: filters });
  return data;
}

export async function getCustomer(customerId) {
  const { data } = await apiClient.get(endpoints.crm.customerDetail(customerId));
  return data;
}

export async function getCustomerActivities(customerId) {
  const { data } = await apiClient.get(endpoints.crm.customerActivities(customerId));
  return data;
}

/**
 * Multi-field matching: ?query= or specific ?email=&phone=&gst=&company=.
 * Returns { match_found, account, contacts, portfolio, recent }.
 */
export async function smartLookup(params) {
  const { data } = await apiClient.get(endpoints.crm.customerSmartLookup, {
    params,
  });
  return data;
}

export async function getPayments(filters) {
  const { data } = await apiClient.get(endpoints.crm.payments, { params: filters });
  return data;
}

export async function recordCustomerPayment(customerId, payload) {
  const { data } = await apiClient.post(endpoints.crm.customerRecordPayment(customerId), payload);
  return data;
}

export async function recordLeadPayment(leadId, payload) {
  const { data } = await apiClient.post(endpoints.crm.leadRecordPayment(leadId), payload);
  return data;
}
