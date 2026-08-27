// Meetings index. Honest G8 state: no list endpoint exists and none can be
// derived (Task exposes no nested meetings), so this page offers creation and
// an open-by-ID lookup until the backend ships GET /tasks/meetings/.

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function MeetingsListPage() {
  const navigate = useNavigate();
  const { resolved } = useAuth();
  const [lookupId, setLookupId] = useState("");
  const canCreate = hasPermission(resolved, "add_meeting");

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Meetings</h1>
        {canCreate ? (
          <Button asChild className="bg-[#2563EB] hover:bg-[#1D4ED8]">
            <Link to="/meetings/new">Request meeting</Link>
          </Button>
        ) : null}
      </div>

      <Card className="rounded-xl border-[#E5E7EB] shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
        <CardHeader>
          <CardTitle className="text-sm">Open a meeting</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            The backend does not provide a meetings list yet (BACKEND_GAPS.md
            G8) — open one by ID, or follow the link from a notification after
            creating it.
          </p>
          <form
            className="flex items-center gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              const id = lookupId.trim();
              if (id) navigate(`/meetings/${id}`);
            }}
          >
            <Input
              placeholder="Meeting ID"
              value={lookupId}
              onChange={(event) => setLookupId(event.target.value)}
            />
            <Button type="submit" variant="outline" disabled={!lookupId.trim()}>
              Open
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
