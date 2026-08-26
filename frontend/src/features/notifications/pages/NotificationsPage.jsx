// Notification inbox: All / Unread tabs, per-item mark-read (idempotent),
// and a bulk "mark all read" that loops the idempotent endpoint client-side
// (no bulk endpoint exists server-side).

import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMarkAllRead, useMarkRead, useNotifications } from "../hooks";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function NotificationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [expandedId, setExpandedId] = useState(null);
  const tab = searchParams.get("tab") === "unread" ? "unread" : "all";

  const filters = tab === "unread" ? { is_read: "false" } : {};
  const inboxQuery = useNotifications(filters);
  const markRead = useMarkRead();
  const markAllRead = useMarkAllRead(
    (inboxQuery.data?.results ?? [])
      .filter((notification) => !notification.is_read)
      .map((notification) => notification.id),
  );

  const notifications = inboxQuery.data?.results ?? inboxQuery.data ?? [];

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Notifications</h1>
        {tab === "unread" && notifications.length > 0 ? (
          <Button variant="outline" size="sm" disabled={markAllRead.isPending} onClick={() => markAllRead.mutateAsync()}>
            Mark all read
          </Button>
        ) : null}
      </div>

      <Tabs value={tab} onValueChange={(value) => setSearchParams({ tab: value })}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="unread">Unread</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Inbox {inboxQuery.data?.count != null ? `(${inboxQuery.data.count})` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {inboxQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : notifications.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {tab === "unread" ? "Nothing unread. 🎉" : "No notifications yet."}
            </p>
          ) : (
            notifications.map((notification) => (
              <button
                key={notification.id}
                type="button"
                onClick={() => setExpandedId(expandedId === notification.id ? null : notification.id)}
                className={[
                  "flex flex-col gap-1 rounded-md border p-3 text-left transition-colors",
                  notification.is_read ? "opacity-70" : "border-l-4 border-l-primary",
                ].join(" ")}
              >
                <div className="flex items-center gap-2">
                  {!notification.is_read ? <Badge>new</Badge> : null}
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {notification.event_type}
                  </Badge>
                  {notification.channel !== "IN_APP" ? (
                    <Badge variant="secondary">{notification.channel}</Badge>
                  ) : null}
                </div>
                <span className={notification.is_read ? "text-sm" : "text-sm font-medium"}>
                  {notification.message.length > 120 && expandedId !== notification.id
                    ? `${notification.message.slice(0, 120)}…`
                    : notification.message}
                </span>
                <span className="text-xs text-muted-foreground">
                  {new Date(notification.created_at).toLocaleString()}
                </span>
                {!notification.is_read && expandedId === notification.id ? (
                  <span
                    role="button"
                    tabIndex={0}
                    className="w-fit text-xs underline"
                    onClick={(event) => {
                      event.stopPropagation();
                      markRead.mutateAsync(notification.id);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.stopPropagation();
                        markRead.mutateAsync(notification.id);
                      }
                    }}
                  >
                    Mark as read
                  </span>
                ) : null}
              </button>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
