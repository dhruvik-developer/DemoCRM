// Activities feed card shared by Lead and Customer detail pages.
// Exactly one of leadId/customerId (backend XOR rule). The "Log activity"
// button is hidden for CONVERTED leads (backend rejects them).

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { useActivities } from "../hooks";
import ActivityCreateDialog from "./ActivityCreateDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function ActivitiesCard({ leadId, customerId, blocked = false }) {
  const { resolved } = useAuth();
  const activitiesQuery = useActivities(
    leadId ? { lead: leadId } : { customer: customerId },
  );
  const [dialogOpen, setDialogOpen] = useState(false);

  const canCreate =
    !blocked && hasPermission(resolved, "add_activity");
  const activities = activitiesQuery.data ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Activities</CardTitle>
        {canCreate ? (
          <Button size="sm" onClick={() => setDialogOpen(true)}>
            Log activity
          </Button>
        ) : null}
        {blocked ? (
          <Badge variant="secondary">Converted — read only</Badge>
        ) : null}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {activitiesQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : activities.length === 0 ? (
          <p className="text-sm text-muted-foreground">No activities recorded yet.</p>
        ) : (
          activities.map((activity) => (
            <div
              key={activity.id}
              className="flex flex-col gap-1 border-b pb-3 last:border-b-0 last:pb-0"
            >
              <div className="flex items-center gap-2">
                <Badge variant="outline">{activity.activity_type}</Badge>
                <span className="text-sm font-medium">{activity.outcome}</span>
                {activity.follow_up_required ? (
                  <Badge variant="secondary">follow-up</Badge>
                ) : null}
              </div>
              {activity.notes ? (
                <p className="text-sm text-muted-foreground">{activity.notes}</p>
              ) : null}
              <span className="text-xs text-muted-foreground">
                {new Date(activity.created_at).toLocaleString()}
              </span>
            </div>
          ))
        )}
      </CardContent>

      <ActivityCreateDialog
        leadId={leadId}
        customerId={customerId}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </Card>
  );
}
