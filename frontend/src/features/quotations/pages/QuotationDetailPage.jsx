// Quotation detail — the full workflow as BUTTONS mirroring backend state
// checks (never a free-form status select):
//   DRAFT → Edit / Submit · PENDING → Approve / Send back (self-approval guard)
//   APPROVED → Send / Email · SENT → Accept (auto-customer!) / Reject (lead→LOST)
// Revision creates a new DRAFT version. PDF is blocked while DRAFT/PENDING.

import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { FormProvider, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useLead } from "@/features/leads/hooks";

import { useAuth } from "@/hooks/useAuth";
import {
  useAcceptQuotation,
  useApproveQuotation,
  useDeleteQuotation,
  useQuotation,
  useRefuseApproval,
  useRefuseQuotation,
  useRequestRevision,
  useSendQuotation,
  useSendQuotationEmail,
  useSubmitQuotation,
  useUpdateDraft,
  downloadQuotationPdf,
} from "../hooks";
import LineItemsEditor from "../components/LineItemsEditor";
import { draftUpdateSchema, rejectQuotationSchema, sendEmailSchema } from "@/schemas/quotation.schema";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import StatusBadge from "@/components/common/StatusBadge";
import FormField from "@/components/forms/FormField";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toMoney } from "@/utils/formatters";

const REVISABLE_STATUSES = ["SENT", "APPROVED", "REVISED"];

export default function QuotationDetailPage() {
  const { quotationId } = useParams();
  const navigate = useNavigate();
  const { user, resolved } = useAuth();
  const quotationQuery = useQuotation(quotationId);

  const [selectedVersionId, setSelectedVersionId] = useState(null);
  const [editingDraft, setEditingDraft] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [acceptOpen, setAcceptOpen] = useState(false);
  const [emailOpen, setEmailOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const submitQuotation = useSubmitQuotation(quotationId);
  const approve = useApproveQuotation(quotationId);
  const sendBack = useRefuseApproval(quotationId);
  const send = useSendQuotation(quotationId);
  const sendEmail = useSendQuotationEmail(quotationId);
  const revise = useRequestRevision(quotationId);
  const accept = useAcceptQuotation(quotationId);
  const refuse = useRefuseQuotation(quotationId);
  const deleteQuotation = useDeleteQuotation();

  const draftForm = useForm({
    resolver: zodResolver(draftUpdateSchema),
  });
  const rejectForm = useForm({
    resolver: zodResolver(rejectQuotationSchema),
    defaultValues: { rejection_reason: "" },
  });
  const emailForm = useForm({
    resolver: zodResolver(sendEmailSchema),
    defaultValues: { recipient_email: "", subject: "", body: "" },
  });
  const leadIdForEmail = quotationQuery.data?.lead ?? quotationQuery.data?.lead_id;
  const leadForEmailQ = useLead(leadIdForEmail);
  useEffect(() => {
    if (emailOpen && leadForEmailQ.data?.email && !emailForm.getValues("recipient_email")) {
      emailForm.setValue("recipient_email", leadForEmailQ.data.email);
      if (!emailForm.getValues("subject")) emailForm.setValue("subject", `Quotation ${quotationQuery.data?.quotation_number ?? ""} from CRM`);
    }
  }, [emailOpen, leadForEmailQ.data, emailForm, quotationQuery.data]);

  if (quotationQuery.isLoading) return <PageLoader label="Loading quotation…" />;
  if (quotationQuery.isError) {
    return <PageError error={quotationQuery.error} onRetry={quotationQuery.refetch} />;
  }

  const quotation = quotationQuery.data;
  const status = quotation.status;
  const versions = quotation.all_versions ?? [];
  const currentVersion =
    versions.find((version) => version.id === (selectedVersionId ?? quotation.current_version)) ??
    quotation.current_version_detail;

  const isLatestDraft =
    status === "DRAFT" &&
    currentVersion?.id === quotation.current_version_detail?.id;

  // Self-approval guard (rule #24): hide Approve when the current user
  // submitted this version and they're not an Admin/superuser (only Admins
  // hold approve_own_quotation under the seed maps).
  const pendingApproval = (currentVersion?.approvals ?? []).find(
    (entry) => entry.decision === "PENDING",
  );
  const submittedByMe =
    pendingApproval?.submitted_by != null &&
    String(pendingApproval.submitted_by) === String(user?.user_id ?? "");
  const canSelfApprove = resolved?.isAdmin;
  const showApprove =
    status === "PENDING_APPROVAL" && (!submittedByMe || canSelfApprove);

  const pdfAllowed = !["DRAFT", "PENDING_APPROVAL"].includes(status);

  const onDownloadPdf = async () => {
    try {
      await downloadQuotationPdf(quotation.id, currentVersion?.version_number);
    } catch {
      // Toasted via normalized error below if we had a hook; keep silent-safe.
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">
            {quotation.quotation_number}
          </h1>
          <StatusBadge status={status} />
        </div>

        {/* Workflow action bar */}
        <div className="flex flex-wrap items-center gap-2">
          {isLatestDraft ? (
            <>
              <Button variant="outline" size="sm" onClick={() => setEditingDraft((value) => !value)}>
                {editingDraft ? "Close editor" : "Edit draft"}
              </Button>
              <Button size="sm" disabled={submitQuotation.isPending} onClick={() => submitQuotation.mutateAsync()}>
                Submit
              </Button>
            </>
          ) : null}

          {showApprove ? (
            <Button size="sm" disabled={approve.isPending} onClick={() => approve.mutateAsync()}>
              Approve
            </Button>
          ) : null}
          {status === "PENDING_APPROVAL" ? (
            <Button
              variant="outline"
              size="sm"
              disabled={sendBack.isPending}
              onClick={() => sendBack.mutateAsync(undefined)}
            >
              Send back to draft
            </Button>
          ) : null}

          {status === "APPROVED" ? (
            <>
              <Button size="sm" disabled={send.isPending} onClick={() => send.mutateAsync()}>
                Mark sent
              </Button>
              <Button variant="outline" size="sm" onClick={() => setEmailOpen(true)}>
                Email…
              </Button>
            </>
          ) : null}

          {status === "SENT" ? (
            <>
              <Button size="sm" onClick={() => setAcceptOpen(true)}>
                Accept…
              </Button>
              <Button variant="destructive" size="sm" onClick={() => setRejectOpen(true)}>
                Reject…
              </Button>
            </>
          ) : null}

          {REVISABLE_STATUSES.includes(status) ? (
            <Button
              variant="outline"
              size="sm"
              disabled={revise.isPending}
              onClick={() => revise.mutateAsync({})}
            >
              New revision
            </Button>
          ) : null}

          <Button
            variant="outline"
            size="sm"
            disabled={!pdfAllowed}
            title={pdfAllowed ? undefined : "PDF is unavailable while the quotation is a draft or pending approval."}
            onClick={onDownloadPdf}
          >
            PDF
          </Button>
          {status === "DRAFT" ? (
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:bg-destructive/10"
              onClick={() => setDeleteOpen(true)}
            >
              Delete draft
            </Button>
          ) : null}
        </div>
      </div>

      {/* Version selector */}
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted-foreground">Version:</span>
        {versions.map((version) => (
          <button
            key={version.id}
            type="button"
            onClick={() => setSelectedVersionId(version.id)}
            className={[
              "rounded-md border px-2 py-1",
              version.id === currentVersion?.id
                ? "border-primary bg-primary text-primary-foreground"
                : "hover:bg-muted",
            ].join(" ")}
          >
            v{version.version_number} · {version.status.toLowerCase()}
          </button>
        ))}
        {currentVersion?.approval_required ? (
          <Badge variant="secondary">approval required</Badge>
        ) : null}
      </div>

      {/* Stitch-styled Quotation Document — real company look with GST */}
      <Card className="overflow-hidden border-outline-variant bg-white shadow-sm">
        {/* Company header */}
        <div className="flex flex-col gap-3 border-b border-outline-variant bg-[#F9FAFB] px-6 py-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex gap-3">
            <div className="hidden h-10 w-10 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-primary to-primary-container font-extrabold text-white sm:grid">S</div>
            <div>
              <div className="text-[18px] font-bold tracking-tight text-[#111214]">DemoCRM Solutions Pvt. Ltd.</div>
              <div className="mt-1 max-w-[360px] text-[11px] leading-relaxed text-muted-foreground">
                100 Tech Park Way, Suite 400, Mumbai – 400001<br />
                GSTIN: 27AABCD1234F1Z5 &nbsp;•&nbsp; CIN: U72200MH2020PTC123456<br />
                info@democrm.com • +91 80055 00199
              </div>
            </div>
          </div>
          <div className="text-left sm:text-right">
            <div className="text-[20px] font-bold tracking-tight text-primary">QUOTATION</div>
            <div className="mt-1 space-y-0.5 text-xs text-muted-foreground">
              <div>Ref: <span className="font-semibold text-foreground">{quotation.quotation_number}</span> • Rev v{currentVersion?.version_number}</div>
              <div className="flex items-center gap-1.5 sm:justify-end"><StatusBadge status={currentVersion?.status ?? status} /><span className="text-[11px]">{currentVersion?.status}</span></div>
            </div>
          </div>
        </div>

        <CardContent className="p-0">
          {/* Prepared For + Overview */}
          <div className="grid gap-6 p-6 sm:grid-cols-2">
            <div>
              <div className="mb-2 border-b border-outline-variant pb-1 text-[11px] font-bold uppercase tracking-wider text-[#6B7280]">Prepared For</div>
              <div className="text-sm font-semibold text-foreground">{quotation.customer?.name ?? leadForEmailQ.data?.name ?? quotation.lead_name ?? "—"}</div>
              <div className="text-xs text-muted-foreground">{quotation.customer?.company_name ?? leadForEmailQ.data?.company_name ?? ""}</div>
              <div className="mt-1 text-xs">
                GSTIN: <span className="font-medium">{leadForEmailQ.data?.metadata?.gst_number ?? leadForEmailQ.data?.metadata?.gst ?? leadForEmailQ.data?.customer_account?.gst_number ?? "—"}</span>
              </div>
              {(leadForEmailQ.data?.metadata?.billing_address || leadForEmailQ.data?.customer_account?.billing_address) && (
                <div className="mt-1 max-w-[280px] text-xs leading-relaxed text-muted-foreground">{leadForEmailQ.data?.metadata?.billing_address ?? leadForEmailQ.data?.customer_account?.billing_address}</div>
              )}
              <div className="mt-2 space-y-0.5 text-xs text-muted-foreground">
                <div>Email: <span className="text-foreground">{quotation.customer?.email ?? leadForEmailQ.data?.email ?? "—"}</span></div>
                <div>Phone: <span className="text-foreground">{quotation.customer?.phone ?? leadForEmailQ.data?.phone ?? "—"}</span></div>
              </div>
            </div>
            <div>
              <div className="mb-2 border-b border-outline-variant pb-1 text-[11px] font-bold uppercase tracking-wider text-[#6B7280]">Quotation Overview</div>
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between"><span className="font-semibold text-[#6B7280] w-24">Date:</span> <span className="font-medium">{currentVersion?.created_at ? new Date(currentVersion.created_at).toLocaleDateString() : "—"}</span></div>
                <div className="flex justify-between"><span className="font-semibold text-[#6B7280] w-24">Valid Until:</span> <span className="font-medium">{currentVersion?.created_at ? new Date(new Date(currentVersion.created_at).getTime() + 30*24*60*60*1000).toLocaleDateString() : "—"}</span></div>
                <div className="flex justify-between"><span className="font-semibold text-[#6B7280] w-24">Status:</span> <span className="font-medium">{currentVersion?.status}</span></div>
                <div className="flex justify-between"><span className="font-semibold text-[#6B7280] w-24">Total:</span> <span className="font-bold tabular-nums">₹{toMoney(currentVersion?.total_amount)}</span></div>
              </div>
            </div>
          </div>

          {/* Line Items Table */}
          <div className="px-6">
            <div className="mb-2 text-[11px] font-bold uppercase tracking-wider text-[#6B7280]">Line Items — Discount & GST per revision</div>
            <div className="overflow-hidden rounded-lg border border-outline-variant">
              <table className="w-full border-collapse text-xs">
                <thead>
                  <tr className="bg-[#F1F5F9] text-[11px] uppercase tracking-wide text-[#334155]">
                    <th className="px-2 py-2 text-left font-bold">Description</th>
                    <th className="px-2 py-2 text-right font-bold">HSN</th>
                    <th className="px-2 py-2 text-right font-bold">Qty</th>
                    <th className="px-2 py-2 text-right font-bold">Unit ₹</th>
                    <th className="px-2 py-2 text-right font-bold">GST%</th>
                    <th className="px-2 py-2 text-right font-bold">Disc%</th>
                    <th className="px-2 py-2 text-right font-bold">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {(currentVersion?.line_items ?? []).map((item) => (
                    <tr key={item.id} className="border-t border-[#E2E8F0] bg-white">
                      <td className="px-2 py-2 font-medium text-foreground">{item.description}</td>
                      <td className="px-2 py-2 text-right text-[11px] text-muted-foreground">{item.hsn_code || "—"}</td>
                      <td className="px-2 py-2 text-right tabular-nums text-muted-foreground">{item.quantity}</td>
                      <td className="px-2 py-2 text-right tabular-nums text-muted-foreground">₹{toMoney(item.unit_price)}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{item.gst_rate != null ? `${Number(item.gst_rate).toFixed(0)}%` : "18%"}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{item.discount_percent ? `${Number(item.discount_percent).toFixed(0)}%` : "—"}</td>
                      <td className="px-2 py-2 text-right tabular-nums font-semibold text-foreground">₹{toMoney(item.amount)}</td>
                    </tr>
                  ))}
                  {(!currentVersion?.line_items || currentVersion.line_items.length === 0) && (
                    <tr><td colSpan={7} className="px-3 py-6 text-center text-muted-foreground">No line items provided.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex justify-end">
              <div className="min-w-[280px] rounded-lg border border-outline-variant bg-[#F9FAFB] px-4 py-3 text-right">
                <div className="flex justify-between text-xs"><span className="text-muted-foreground">Subtotal</span><span className="font-medium tabular-nums">₹{toMoney(currentVersion?.subtotal_amount ?? currentVersion?.subtotal ?? currentVersion?.total_amount)}</span></div>
                {currentVersion?.discount_value && Number(currentVersion.discount_value) !== 0 ? (
                  <div className="flex justify-between text-xs text-amber-700"><span>Discount {currentVersion.discount_type === "PERCENT" ? `(${currentVersion.discount_value}%)` : ""}</span><span>- ₹{toMoney(currentVersion.discount_amount ?? 0)}</span></div>
                ) : null}
                {currentVersion?.gst_rate && Number(currentVersion.gst_rate) !== 0 ? (
                  <>
                    <div className="flex justify-between text-xs text-muted-foreground"><span>CGST {(Number(currentVersion.gst_rate)/2).toFixed(1)}%</span><span>₹{toMoney(Number(currentVersion.gst_amount ?? 0)/2)}</span></div>
                    <div className="flex justify-between text-xs text-muted-foreground"><span>SGST {(Number(currentVersion.gst_rate)/2).toFixed(1)}%</span><span>₹{toMoney(Number(currentVersion.gst_amount ?? 0)/2)}</span></div>
                    <div className="flex justify-between text-xs font-medium text-muted-foreground"><span>GST Total {Number(currentVersion.gst_rate).toFixed(0)}%</span><span>₹{toMoney(currentVersion.gst_amount ?? 0)}</span></div>
                  </>
                ) : (
                  <div className="flex justify-between text-xs text-muted-foreground"><span>GST</span><span>Not applicable</span></div>
                )}
                <div className="mt-1 flex justify-between border-t border-outline-variant pt-2 text-sm font-bold"><span>Total Amount</span><span className="tabular-nums">₹{toMoney(currentVersion?.total_amount)}</span></div>
                <div className="mt-1 text-[10px] text-muted-foreground">Valid 30 days • {currentVersion?.status}</div>
              </div>
            </div>
          </div>

          {/* Terms & Notes + Footer */}
          {(currentVersion?.terms || currentVersion?.notes || currentVersion?.rejection_reason) && (
            <div className="mx-6 mt-6 rounded-lg border-l-4 border-[#94A3B8] bg-[#F8FAFC] p-3 text-xs leading-relaxed">
              {currentVersion?.terms && <div className="mb-1"><span className="font-bold">Terms & Conditions:</span> {currentVersion.terms}</div>}
              {currentVersion?.notes && <div><span className="font-bold">Notes:</span> {currentVersion.notes}</div>}
              {currentVersion?.rejection_reason && <div className="mt-1 text-destructive"><span className="font-bold">Rejected:</span> {currentVersion.rejection_reason}</div>}
            </div>
          )}
          <div className="mx-6 mt-6 border-t border-outline-variant pt-3 text-center text-[11px] leading-relaxed text-[#94A3B8]">
            This is an official quotation from DemoCRM Solutions Pvt. Ltd. • GSTIN: 27AABCD1234F1Z5<br />
            Thank you for your business. For queries, contact info@democrm.com
          </div>
          <div className="h-4" />
        </CardContent>
      </Card>

      {isLatestDraft && editingDraft ? (
        <DraftEditor quotationId={quotation.id} current={currentVersion} form={draftForm} onClose={() => setEditingDraft(false)} />
      ) : null}

      <Link to="/quotations" className="text-sm text-muted-foreground hover:underline">
        ← All quotations
      </Link>

      {/* Reject (client rejection → lead marked LOST) */}
      <ConfirmDialog
        open={rejectOpen}
        onOpenChange={setRejectOpen}
        title="Reject this quotation?"
        description="The originating lead will be marked LOST with this reason."
        confirmLabel="Reject"
        destructive
        loading={refuse.isPending}
        onConfirm={rejectForm.handleSubmit((values) =>
          refuse.mutateAsync(values.rejection_reason).then(() => setRejectOpen(false)),
        )}
      >
        <FormField
          id="rejection_reason"
          label="Reason (required)"
          error={rejectForm.formState.errors.rejection_reason?.message}
        >
          <textarea
            id="rejection_reason"
            rows={3}
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm"
            {...rejectForm.register("rejection_reason")}
          />
        </FormField>
      </ConfirmDialog>

      {/* Accept (auto-converts lead into a customer) */}
      <ConfirmDialog
        open={acceptOpen}
        onOpenChange={setAcceptOpen}
        title="Accept this quotation?"
        description="This will automatically convert the originating lead into a Customer."
        confirmLabel="Accept & create customer"
        loading={accept.isPending}
        onConfirm={() => accept.mutateAsync().then(() => setAcceptOpen(false))}
      />

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete draft quotation?"
        description={`This will permanently delete ${quotation.quotation_number} (draft). Sent/accepted quotations cannot be deleted.`}
        confirmLabel="Delete draft"
        destructive
        loading={deleteQuotation.isPending}
        onConfirm={() => deleteQuotation.mutateAsync(quotation.id).then(() => { setDeleteOpen(false); navigate("/quotations"); })}
      />

      {/* Send email dialog */}
      <Dialog open={emailOpen} onOpenChange={setEmailOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Email quotation</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={emailForm.handleSubmit((values) =>
              sendEmail
                .mutateAsync({
                  recipient_email: values.recipient_email,
                  subject: values.subject || undefined,
                  body: values.body || undefined,
                })
                .then(() => setEmailOpen(false)),
            )}
            className="flex flex-col gap-3"
          >
            <FormField
              id="recipient_email"
              label="Recipient"
              error={emailForm.formState.errors.recipient_email?.message}
            >
              <Input id="recipient_email" type="email" {...emailForm.register("recipient_email")} />
            </FormField>
            <FormField id="subject" label="Subject (optional)">
              <Input id="subject" {...emailForm.register("subject")} />
            </FormField>
            <FormField id="body" label="Message (optional)">
              <Textarea id="body" rows={3} {...emailForm.register("body")} />
            </FormField>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEmailOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={sendEmail.isPending}>
                {sendEmail.isPending ? "Sending…" : "Send email"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function DraftEditor({ quotationId, current, form, onClose }) {
  const updateDraftMutation = useUpdateDraft(quotationId);

  const methods = form;
  const initialTotal = useMemo(
    () =>
      (current?.line_items ?? []).reduce(
        (sum, item) => sum + Number(item.quantity) * Number(item.unit_price),
        0,
      ),
    [current],
  );

  // Seed the editor when it opens; reset() syncs an external system (RHF).
  useEffect(() => {
    methods.reset({
      terms: current?.terms ?? "",
      notes: current?.notes ?? "",
      discount_type: current?.discount_type ?? "FLAT",
      discount_value: current?.discount_value ?? 0,
      gst_rate: current?.gst_rate ?? 0,
      line_items: (current?.line_items ?? []).map((item) => ({
        description: item.description,
        hsn_code: item.hsn_code ?? "",
        quantity: item.quantity,
        unit_price: item.unit_price,
        gst_rate: item.gst_rate ?? 18,
        discount_percent: item.discount_percent ?? 0,
      })),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <FormProvider {...methods}>
      <Card>
        <CardHeader>
          <CardTitle>Edit draft</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <FormField id="draft_discount_type" label="Discount type">
              <select id="draft_discount_type" className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm" {...methods.register("discount_type")}>
                <option value="FLAT">Flat (₹)</option>
                <option value="PERCENT">Percent (%)</option>
              </select>
            </FormField>
            <FormField id="draft_discount_value" label="Discount value">
              <Input id="draft_discount_value" type="number" step={0.01} placeholder="0 — per revision (v1 none, v2 can add)" {...methods.register("discount_value")} />
            </FormField>
            <FormField id="draft_gst_rate" label="GST rate % (0 = not applicable)">
              <Input id="draft_gst_rate" type="number" step={0.1} placeholder="0 or 18" {...methods.register("gst_rate")} />
            </FormField>
          </div>
          <p className="text-xs text-muted-foreground">Discount & GST are <span className="font-semibold">per revision</span> — v1 can have none, v2 can add discount/GST. Stored per version.</p>
          <FormField id="draft_terms" label="Terms">
            <Textarea id="draft_terms" rows={2} {...methods.register("terms")} />
          </FormField>
          <FormField id="draft_notes" label="Notes">
            <Textarea id="draft_notes" rows={2} {...methods.register("notes")} />
          </FormField>
          <LineItemsEditor />

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              Server-side check: line items must sum exactly to the total{" "}
              ({toMoney(initialTotal)} at load).
            </span>
            <div className="flex gap-2">
              <Button type="button" variant="ghost" onClick={onClose}>
                Cancel
              </Button>
              <Button
                type="button"
                disabled={updateDraftMutation.isPending || !methods.formState.isDirty}
                onClick={methods.handleSubmit((values) =>
                  updateDraftMutation.mutateAsync(values).then(onClose),
                )}
              >
                {updateDraftMutation.isPending ? "Saving…" : "Save draft"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </FormProvider>
  );
}
