// Customer detail: profile + Lead→Customer relationship (post-conversion
// traceability) + activities via the shared ActivitiesCard.

import { Link, useParams } from "react-router-dom";
import { useCustomer } from "../hooks";
import ActivitiesCard from "@/features/activities/components/ActivitiesCard";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function Field({ label, value }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="text-sm">{value ?? "—"}</span>
    </div>
  );
}

export default function CustomerDetailPage() {
  const { customerId } = useParams();
  const customerQuery = useCustomer(customerId);

  if (customerQuery.isLoading) return <PageLoader label="Loading customer…" />;
  if (customerQuery.isError) {
    return <PageError error={customerQuery.error} onRetry={customerQuery.refetch} />;
  }

  const customer = customerQuery.data;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">{customer.name}</h1>
        <Button variant="ghost" asChild>
          <Link to="/customers">← All customers</Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="Email" value={customer.email} />
          <Field label="Phone" value={customer.phone} />
          <Field label="Company" value={customer.company_name} />
          <Field
            label="Created"
            value={
              customer.created_at
                ? new Date(customer.created_at).toLocaleString()
                : null
            }
          />
          <div className="flex flex-col gap-1 md:col-span-2">
            <span className="text-xs uppercase tracking-wide text-muted-foreground">
              Originating lead
            </span>
            {customer.lead ? (
              <Link
                to={`/leads/${customer.lead}`}
                className="inline-flex w-fit items-center gap-2 text-sm hover:underline"
              >
                View lead
                <Badge variant="outline" className="font-mono text-[10px]">
                  {String(customer.lead).slice(0, 8)}…
                </Badge>
              </Link>
            ) : (
              <span className="text-sm">—</span>
            )}
          </div>
        </CardContent>
      </Card>

      <ActivitiesCard customerId={customer.id} />
    </div>
  );
}
