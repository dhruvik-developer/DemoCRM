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
  const page = Math.max(1, parseInt(searchParams.get("page") || "1", 10) || 1);
  const pageSize = 20;

  const filters = { ...(tab === "unread" ? { is_read: "false" } : {}), page, page_size: pageSize };
  const inboxQuery = useNotifications(filters);
  const markRead = useMarkRead();

  const raw = inboxQuery.data;
  const isPaginated = Array.isArray(raw?.results);
  const allNotifications = isPaginated ? raw.results : Array.isArray(raw) ? raw : [];
  const totalCount = raw?.count ?? allNotifications.length;
  const totalPages = raw?.num_pages ?? Math.max(1, Math.ceil(totalCount / pageSize));
  const notifications = isPaginated ? allNotifications : allNotifications.slice((page - 1) * pageSize, page * pageSize);

  const markAllRead = useMarkAllRead(
    allNotifications.filter((n) => !n.is_read).map((n) => n.id),
  );

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

      <Tabs value={tab} onValueChange={(value) => setSearchParams({ tab: value, page: "1" })}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="unread">Unread</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Inbox {totalCount ? `(${totalCount})` : ""}
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
          {/* Pagination — 10 per page, client fallback if backend not restarted */}
          {totalPages > 1 ? (
            <div className="flex items-center justify-between border-t pt-4">
              <span className="text-xs text-muted-foreground">
                Page {page} of {totalPages} • {totalCount} total
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setSearchParams({ tab, page: String(page - 1) })}
                >
                  Prev
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setSearchParams({ tab, page: String(page + 1) })}
                >
                  Next
                </Button>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
