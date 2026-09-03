// Customer detail — Stitch polished (Minimalist/Corporate Modern)
// Flat white surfaces, 1px #E5E7EB borders, 8px grid, 12px cards, 36px controls, Geist.

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useCustomer, useSmartLookup, usePayments, useRecordCustomerPayment } from "../hooks";
import { useQuotations } from "@/features/quotations/hooks";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import ActivitiesCard from "@/features/activities/components/ActivitiesCard";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import StatusBadge from "@/components/common/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import FormField from "@/components/forms/FormField";

function Field({ label, value }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[#6B7280]">{label}</span>
      <span className="text-sm text-[#111214]">{value ?? "—"}</span>
    </div>
  );
}

function Money({ value }) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const paymentSchema = z.object({
  amount: z.coerce.number().positive("Amount must be > 0"),
  payment_date: z.string().optional(),
  method: z.enum(["CASH", "BANK_TRANSFER", "UPI", "CHEQUE", "ONLINE", "OTHER"]),
  reference: z.string().optional(),
  notes: z.string().optional(),
});

function RecordPaymentDialog({ open, onOpenChange, customer, dueAmount, onSuccess }) {
  const { resolved } = useAuth();
  const canRecord = hasPermission(resolved, "record_payment") || resolved?.isAdmin;
  const record = useRecordCustomerPayment(customer?.id);
  const { register, handleSubmit, reset, formState: { errors } } = useForm({
    resolver: zodResolver(paymentSchema),
    defaultValues: { amount: "", payment_date: new Date().toISOString().slice(0, 10), method: "CASH", reference: "", notes: "" },
  });
  if (!canRecord) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-[12px] border border-[#E5E7EB] bg-white p-6">
        <DialogHeader className="pb-3 border-b border-[#E5E7EB]"><DialogTitle className="text-[18px] font-semibold tracking-tight text-[#111214]">Record payment — {customer?.name}</DialogTitle></DialogHeader>
        <p className="pt-3 text-xs leading-5 text-[#6B7280]">Outstanding due: <span className="font-semibold text-[#111214]"><Money value={dueAmount} /></span> • Total syncs from accepted quotation. Status: <span className="font-medium">NO_DUES / PARTIALLY_PAID / PAYMENT_OVERDUE</span>.</p>
        <form onSubmit={handleSubmit((vals) => record.mutateAsync({ amount: vals.amount, payment_date: vals.payment_date || undefined, method: vals.method, reference: vals.reference || undefined, notes: vals.notes || undefined }).then(() => { reset(); onOpenChange(false); onSuccess?.(); }))} className="flex flex-col gap-3 pt-1">
          <FormField id="pay_amount" label={`Amount (max ₹${Number(dueAmount).toLocaleString("en-IN")})`} error={errors.amount?.message}><Input id="pay_amount" type="number" step="0.01" placeholder="e.g. 10000" className="h-9 border-[#D1D5DB] focus-visible:border-[#2563EB] focus-visible:ring-1 focus-visible:ring-[#2563EB]" {...register("amount")} /></FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField id="pay_date" label="Date" error={errors.payment_date?.message}><Input id="pay_date" type="date" className="h-9 border-[#D1D5DB] focus-visible:border-[#2563EB] focus-visible:ring-1 focus-visible:ring-[#2563EB]" {...register("payment_date")} /></FormField>
            <FormField id="pay_method" label="Method">
              <select id="pay_method" className="flex h-9 w-full rounded-md border border-[#D1D5DB] bg-white px-3 py-1 text-sm focus:border-[#2563EB] focus:outline-none focus:ring-1 focus:ring-[#2563EB]" {...register("method")}>
                <option value="CASH">Cash</option>
                <option value="BANK_TRANSFER">Bank Transfer</option>
                <option value="UPI">UPI</option>
                <option value="CHEQUE">Cheque</option>
                <option value="ONLINE">Online Gateway</option>
                <option value="OTHER">Other</option>
              </select>
            </FormField>
          </div>
          <FormField id="pay_ref" label="Reference (optional)"><Input id="pay_ref" placeholder="Txn ID / Cheque No." className="h-9 border-[#D1D5DB] focus-visible:border-[#2563EB] focus-visible:ring-1 focus-visible:ring-[#2563EB]" {...register("reference")} /></FormField>
          <FormField id="pay_notes" label="Notes (optional)"><Textarea id="pay_notes" rows={2} className="border-[#D1D5DB] focus-visible:border-[#2563EB] focus-visible:ring-1 focus-visible:ring-[#2563EB]" {...register("notes")} /></FormField>
          <DialogFooter className="pt-3 border-t border-[#E5E7EB]">
            <Button type="button" variant="outline" className="h-9 border-[#E5E7EB] text-[#111214]" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={record.isPending} className="h-9 bg-[#2563EB] hover:bg-[#1D4ED8] text-white px-4">{record.isPending ? "Saving…" : "Record payment"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function CustomerDetailPage() {
  const { customerId } = useParams();
  const [payOpen, setPayOpen] = useState(false);
  const customerQuery = useCustomer(customerId);
  const customer = customerQuery.data;
  const lookupQuery = useSmartLookup(
    customer ? { email: customer.email || undefined, phone: customer.phone || undefined, company_name: customer.company_name || undefined } : {}
  );
  const quotationsQuery = useQuotations(customer?.lead ? { lead: customer.lead } : {});
  const paymentsQuery = usePayments(customer ? { customer: customer.id } : {});

  if (customerQuery.isLoading) return <PageLoader label="Loading customer…" />;
  if (customerQuery.isError) return <PageError error={customerQuery.error} onRetry={customerQuery.refetch} />;

  const lookup = lookupQuery.data;
  const portfolio = lookup?.portfolio;
  const recent = lookup?.recent_engagements ?? lookup?.recent ?? [];
  const quotations = quotationsQuery.data?.results ?? quotationsQuery.data ?? [];
  let totalValue = recent.reduce((s, r) => s + (Number(r.total_value) || 0), 0);
  let paidAmount = recent.reduce((s, r) => s + (Number(r.paid_amount) || 0), 0);
  let dueAmount = recent.reduce((s, r) => s + (Number(r.due_amount) || 0), 0);
  const acceptedQuotations = quotations.filter((q) => q.status === "ACCEPTED");
  const quotationAcceptedTotal = acceptedQuotations.reduce((s, q) => {
    const amt = q.current_version_detail?.total_amount ?? q.accepted_version_detail?.total_amount ?? q.current_version?.total_amount ?? 0;
    return s + (Number(amt) || 0);
  }, 0);
  if (totalValue === 0 && quotationAcceptedTotal > 0) {
    totalValue = quotationAcceptedTotal;
    dueAmount = quotationAcceptedTotal - paidAmount;
  }
  const effectiveDue = portfolio?.total_outstanding_dues ?? dueAmount;
  let effectiveFinancialStatus = portfolio?.financial_status;
  if (!effectiveFinancialStatus) {
    if (totalValue === 0) effectiveFinancialStatus = "NO_DUES";
    else if (effectiveDue <= 0) effectiveFinancialStatus = "NO_DUES";
    else if (paidAmount > 0) effectiveFinancialStatus = "PARTIALLY_PAID";
    else effectiveFinancialStatus = "PAYMENT_OVERDUE";
  }
  const payments = paymentsQuery.data ?? [];
  const paymentList = Array.isArray(payments) ? payments : payments.results ?? [];

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[30px] font-bold tracking-[-0.02em] leading-9 text-[#111214]">{customer.name}</h1>
          <p className="text-sm text-[#6B7280]">Customer • {customer.company_name || "Individual"} • Created {customer.created_at ? new Date(customer.created_at).toLocaleDateString() : "—"}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button className="h-9 bg-[#2563EB] hover:bg-[#1D4ED8] text-white px-4 text-sm font-medium" onClick={() => setPayOpen(true)}>Record payment</Button>
          <Button variant="ghost" asChild className="h-9 text-[#6B7280] hover:text-[#111214]"><Link to="/customers">← All customers</Link></Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2 rounded-[12px] border border-[#E5E7EB] bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <CardHeader className="pb-3 border-b border-[#E5E7EB]"><CardTitle className="text-[14px] font-semibold text-[#111214]">Profile</CardTitle><CardDescription className="text-xs text-[#6B7280]">Originating lead {customer.lead ? String(customer.lead).slice(0, 8) : "—"} • {customer.email} • {customer.phone}</CardDescription></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2 p-6">
            <Field label="Email" value={customer.email} />
            <Field label="Phone" value={customer.phone} />
            <Field label="Company" value={customer.company_name} />
            <Field label="Created" value={customer.created_at ? new Date(customer.created_at).toLocaleString() : null} />
            <div className="flex flex-col gap-1 md:col-span-2">
              <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[#6B7280]">Originating lead</span>
              {customer.lead ? (
                <Link to={`/leads/${customer.lead}`} className="inline-flex w-fit items-center gap-2 text-sm text-[#2563EB] hover:underline">
                  View lead <Badge variant="outline" className="font-mono text-[10px] border-[#E5E7EB] text-[#111214]">{String(customer.lead).slice(0, 8)}…</Badge>
                </Link>
              ) : <span className="text-sm text-[#6B7280]">—</span>}
            </div>
            {lookup?.account ? (
              <div className="md:col-span-2 rounded-[8px] border border-[#E5E7EB] bg-[#f9f9ff] p-3">
                <div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[#6B7280]">Linked Account</div>
                <div className="mt-1 text-sm font-medium text-[#111214]">{lookup.account.company_name} {lookup.account.gst_number ? `• GST ${lookup.account.gst_number}` : ""}</div>
                {lookup.account.website ? <div className="text-xs text-[#6B7280]">{lookup.account.website} • {lookup.account.primary_phone || ""}</div> : null}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card className="rounded-[12px] border border-[#E5E7EB] bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <CardHeader className="pb-3 border-b border-[#E5E7EB]"><CardTitle className="text-[14px] font-semibold text-[#111214]">Portfolio Overview</CardTitle><CardDescription className="text-xs text-[#6B7280]">Across all pipelines for this account/contact</CardDescription></CardHeader>
          <CardContent className="flex flex-col gap-3 p-6">
            {lookupQuery.isLoading ? <p className="text-sm text-[#6B7280]">Loading portfolio…</p> : lookup?.match_found ? (
              <>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-[8px] border border-[#E5E7EB] bg-white p-3"><div className="text-lg font-bold text-[#111214]">{portfolio?.total_engagements ?? recent.length}</div><div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[#6B7280]">Projects</div></div>
                  <div className="rounded-[8px] border border-[#E5E7EB] bg-white p-3"><div className="text-lg font-bold text-[#059669]">{portfolio?.active_engagements ?? 0}</div><div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[#6B7280]">Active</div></div>
                  <div className="rounded-[8px] border border-[#E5E7EB] bg-white p-3"><div className="text-lg font-bold text-[#2563EB]">{portfolio?.completed_engagements ?? 0}</div><div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[#6B7280]">Completed</div></div>
                </div>
                <div className="rounded-[8px] border border-[#E5E7EB] bg-[#f9f9ff] p-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[#6B7280]">Outstanding dues</div>
                  <div className="text-lg font-bold text-[#B45309]"><Money value={effectiveDue} /></div>
                  <div className="text-xs text-[#6B7280]">Total <Money value={totalValue} /> • Paid <Money value={paidAmount} /></div>
                  {quotationAcceptedTotal > 0 && totalValue === quotationAcceptedTotal ? <div className="mt-1 text-[11px] text-[#059669]">Derived from {acceptedQuotations.length} accepted quotation(s)</div> : null}
                </div>
                {lookup?.contacts?.length ? (
                  <div className="pt-2 border-t border-[#E5E7EB]">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[#6B7280]">Contacts</div>
                    {(lookup.contacts || []).slice(0, 3).map((c) => <div key={c.id} className="mt-1 text-xs text-[#111214]">{c.name} — {c.email || c.phone}</div>)}
                  </div>
                ) : null}
              </>
            ) : <p className="text-sm text-[#6B7280]">No portfolio data yet. This customer will accumulate projects as more leads for {customer.company_name || customer.email} are created and converted.</p>}
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[12px] border border-[#E5E7EB] bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
        <CardHeader className="pb-3 border-b border-[#E5E7EB]"><CardTitle className="text-[14px] font-semibold text-[#111214]">Projects (all engagements for this account)</CardTitle><CardDescription className="text-xs text-[#6B7280]">Each lead is a project/engagement. Income tracked per engagement.</CardDescription></CardHeader>
        <CardContent className="p-0">
          {recent.length === 0 ? <p className="py-6 text-center text-sm text-[#6B7280] px-6">Only this customer so far. Create more leads with the same company/GST to see them grouped here.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="h-[44px] border-b border-[#E5E7EB] text-[11px] font-semibold uppercase tracking-[0.05em] text-[#6B7280]">
                    <th className="px-4 text-left">Project</th>
                    <th className="px-4 text-left">Pipeline</th>
                    <th className="px-4 text-left">Stage</th>
                    <th className="px-4 text-left">Status</th>
                    <th className="px-4 text-right">Total</th>
                    <th className="px-4 text-right">Paid</th>
                    <th className="px-4 text-right">Due</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((r) => (
                    <tr key={r.id} className="h-[44px] border-b border-[#E5E7EB] last:border-0 hover:bg-[#f9f9ff]">
                      <td className="px-4"><Link to={`/leads/${r.id}`} className="font-medium text-[#111214] hover:text-[#2563EB] hover:underline">{r.title}</Link></td>
                      <td className="px-4 text-xs text-[#6B7280]">{r.pipeline_name} {r.entity_label ? `(${r.entity_label})` : ""}</td>
                      <td className="px-4 text-xs text-[#6B7280]">{r.current_stage}</td>
                      <td className="px-4"><StatusBadge status={r.status} /><span className="ml-2 text-xs text-[#6B7280]">{r.financial_status}</span></td>
                      <td className="px-4 text-right text-[#111214]"><Money value={r.total_value} /></td>
                      <td className="px-4 text-right text-[#059669]"><Money value={r.paid_amount} /></td>
                      <td className="px-4 text-right text-[#B45309]"><Money value={r.due_amount} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-[12px] border border-[#E5E7EB] bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <CardHeader className="pb-3 border-b border-[#E5E7EB]"><CardTitle className="text-[14px] font-semibold text-[#111214]">Quotations</CardTitle><CardDescription className="text-xs text-[#6B7280]">Linked to the originating lead (and account)</CardDescription></CardHeader>
          <CardContent className="p-6">
            {quotationsQuery.isLoading ? <p className="text-sm text-[#6B7280]">Loading…</p> : quotations.length === 0 ? <p className="text-sm text-[#6B7280]">No quotations for this customer yet.</p> : (
              <div className="flex flex-col gap-2">
                {quotations.slice(0, 5).map((q) => (
                  <Link key={q.id} to={`/quotations/${q.id}`} className="flex items-center justify-between rounded-[8px] border border-[#E5E7EB] bg-white px-3 py-3 hover:border-[#2563EB]/30 hover:bg-[#f9f9ff]">
                    <div><div className="text-sm font-medium text-[#111214]">{q.quotation_number}</div><div className="text-xs text-[#6B7280]">{q.status} • {q.current_version_detail?.total_amount ? `₹${Number(q.current_version_detail.total_amount).toLocaleString("en-IN")}` : ""}</div></div>
                    <Badge variant="outline" className="border-[#E5E7EB] text-[11px] font-semibold text-[#111214]">{q.status}</Badge>
                  </Link>
                ))}
                {quotations.length > 5 ? <Link to={`/quotations?lead=${customer.lead}`} className="text-xs font-medium text-[#2563EB] hover:underline">View all →</Link> : null}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-[12px] border border-[#E5E7EB] bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <CardHeader className="pb-3 border-b border-[#E5E7EB]"><CardTitle className="text-[14px] font-semibold text-[#111214]">Income Summary</CardTitle><CardDescription className="text-xs text-[#6B7280]">From pipeline engagements • Manual payments update status</CardDescription></CardHeader>
          <CardContent className="flex flex-col gap-3 p-6">
            <div className="flex justify-between text-sm"><span className="text-[#6B7280]">Total Value</span><span className="font-semibold text-[#111214]"><Money value={totalValue} /></span></div>
            <div className="flex justify-between text-sm"><span className="text-[#6B7280]">Paid Amount</span><span className="font-semibold text-[#059669]"><Money value={paidAmount} /></span></div>
            <div className="flex justify-between text-sm"><span className="text-[#6B7280]">Due Amount</span><span className="font-semibold text-[#B45309]"><Money value={effectiveDue} /></span></div>
            <div className="flex items-center gap-2 pt-1">
              <Badge className={effectiveFinancialStatus === "NO_DUES" ? "bg-[#F0FDF4] text-[#166534] border-[#BBF7D0]" : effectiveFinancialStatus === "PARTIALLY_PAID" ? "bg-[#FFFBEB] text-[#92400E] border-[#FDE68A]" : "bg-[#FEF2F2] text-[#991B1B] border-[#FECACA]"}>{effectiveFinancialStatus}</Badge>
              <span className="text-xs text-[#6B7280]">{effectiveDue <= 0 && totalValue > 0 ? "Fully paid" : paidAmount > 0 ? "Partially paid" : "Unpaid"}</span>
            </div>
            <Button size="sm" className="mt-1 h-9 bg-[#2563EB] hover:bg-[#1D4ED8] text-white" onClick={() => setPayOpen(true)}>Record payment</Button>
            <div className="mt-2 rounded-[8px] bg-[#FFFBEB] border border-[#FDE68A] px-3 py-2 text-xs leading-5 text-[#92400E]">Outstanding dues = sum of due_amount across all engagements. Financial status rolls up as <span className="font-semibold">{effectiveFinancialStatus}</span>.</div>
            {quotationAcceptedTotal > 0 ? <div className="text-[11px] text-[#6B7280]">Accepted quotations total: <Money value={quotationAcceptedTotal} /> ({acceptedQuotations.length})</div> : null}
            {paymentList.length > 0 ? (
              <div className="mt-2 border-t border-[#E5E7EB] pt-3">
                <div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[#6B7280]">Payment history</div>
                <div className="mt-2 flex flex-col gap-1.5">
                  {paymentList.slice(0, 5).map((p) => (
                    <div key={p.id} className="flex items-center justify-between rounded-[8px] border border-[#E5E7EB] bg-[#f9f9ff] px-3 py-2 text-xs">
                      <span className="text-[#111214]"><Money value={p.amount} /> • {p.method} {p.reference ? `• ${p.reference}` : ""}</span>
                      <span className="text-[#6B7280]">{p.payment_date ? new Date(p.payment_date).toLocaleDateString() : ""}</span>
                    </div>
                  ))}
                  {paymentList.length > 5 ? <span className="text-[11px] text-[#6B7280]">{paymentList.length - 5} more…</span> : null}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <ActivitiesCard customerId={customer.id} />
      <RecordPaymentDialog open={payOpen} onOpenChange={setPayOpen} customer={customer} dueAmount={effectiveDue} onSuccess={() => { customerQuery.refetch(); lookupQuery.refetch(); quotationsQuery.refetch(); paymentsQuery.refetch(); }} />
    </div>
  );
}
