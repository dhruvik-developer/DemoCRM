// Quotation detail — the full workflow as BUTTONS mirroring backend state
// checks (never a free-form status select):
//   DRAFT → Edit / Submit · PENDING → Approve / Send back (self-approval guard)
//   APPROVED → Send / Email · SENT → Accept (auto-customer!) / Reject (lead→LOST)
// Revision creates a new DRAFT version. PDF is blocked while DRAFT/PENDING.

import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { FormProvider, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useLead } from "@/features/leads/hooks";

import { useAuth } from "@/hooks/useAuth";
import {
  useAcceptQuotation,
  useApproveQuotation,
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
  const { user, resolved } = useAuth();
  const quotationQuery = useQuotation(quotationId);

  const [selectedVersionId, setSelectedVersionId] = useState(null);
  const [editingDraft, setEditingDraft] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [acceptOpen, setAcceptOpen] = useState(false);
  const [emailOpen, setEmailOpen] = useState(false);

  const submitQuotation = useSubmitQuotation(quotationId);
  const approve = useApproveQuotation(quotationId);
  const sendBack = useRefuseApproval(quotationId);
  const send = useSendQuotation(quotationId);
  const sendEmail = useSendQuotationEmail(quotationId);
  const revise = useRequestRevision(quotationId);
  const accept = useAcceptQuotation(quotationId);
  const refuse = useRefuseQuotation(quotationId);

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

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Line items — v{currentVersion?.version_number}</CardTitle>
          <span className="text-lg font-semibold tabular-nums">
            {toMoney(currentVersion?.total_amount)}
          </span>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {(currentVersion?.line_items ?? []).map((item) => (
            <div key={item.id} className="flex items-center justify-between border-b pb-2 text-sm last:border-b-0 last:pb-0">
              <span>{item.description}</span>
              <span className="tabular-nums text-muted-foreground">
                {item.quantity} × {toMoney(item.unit_price)} ={" "}
                <span className="font-medium text-foreground">{toMoney(item.amount)}</span>
              </span>
            </div>
          ))}
          {(currentVersion?.terms) ? (
            <p className="pt-2 text-xs text-muted-foreground">Terms: {currentVersion.terms}</p>
          ) : null}
          {currentVersion?.rejection_reason ? (
            <p className="pt-2 text-xs text-destructive">
              Rejected: {currentVersion.rejection_reason}
            </p>
          ) : null}
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
      line_items: (current?.line_items ?? []).map((item) => ({
        description: item.description,
        quantity: item.quantity,
        unit_price: item.unit_price,
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
