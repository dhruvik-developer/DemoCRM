// Notification inbox: All / Unread tabs, per-item mark-read (idempotent),
// and a bulk "mark all read" that loops the idempotent endpoint client-side.

import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bell, CheckCheck, Inbox } from "lucide-react";
import { useMarkAllRead, useMarkRead, useNotifications } from "../hooks";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

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
    <div className="mx-auto flex w-full max-w-[1000px] flex-col gap-6 p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-[26px] font-bold tracking-tight text-foreground">Notifications & Alerts</h1>
          <p className="text-[13px] text-muted-foreground mt-0.5">Stay informed on pipeline activity, task deadlines, and quotation updates.</p>
        </div>
        {tab === "unread" && notifications.length > 0 ? (
          <Button
            variant="outline"
            size="sm"
            className="rounded-[9px] text-xs h-8.5"
            disabled={markAllRead.isPending}
            onClick={() => markAllRead.mutateAsync()}
          >
            <CheckCheck className="h-3.5 w-3.5 mr-1 text-primary" /> Mark all read
          </Button>
        ) : null}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setSearchParams({ tab: "all", page: "1" })}
          className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
            tab === "all"
              ? "bg-primary-soft border-primary/30 text-primary shadow-xs"
              : "bg-surface border-border text-muted-foreground hover:text-foreground hover:bg-muted/50"
          }`}
        >
          <Inbox className="h-3.5 w-3.5" /> All Notifications ({totalCount})
        </button>
        <button
          type="button"
          onClick={() => setSearchParams({ tab: "unread", page: "1" })}
          className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
            tab === "unread"
              ? "bg-primary-soft border-primary/30 text-primary shadow-xs"
              : "bg-surface border-border text-muted-foreground hover:text-foreground hover:bg-muted/50"
          }`}
        >
          <Bell className="h-3.5 w-3.5" /> Unread only
        </button>
      </div>

      {/* Notifications List */}
      <Card className="rounded-[18px] border-border bg-surface shadow-sm overflow-hidden">
        <CardContent className="p-0 divide-y divide-border">
          {inboxQuery.isLoading ? (
            <div className="p-8 text-center text-xs text-muted-foreground">Loading notifications…</div>
          ) : notifications.length === 0 ? (
            <div className="p-12 text-center space-y-2">
              <div className="w-10 h-10 rounded-full bg-primary-soft text-primary flex items-center justify-center mx-auto">
                <CheckCheck className="h-5 w-5" />
              </div>
              <p className="text-sm font-semibold text-foreground">All caught up!</p>
              <p className="text-xs text-muted-foreground">{tab === "unread" ? "You have no unread notifications." : "No notifications in your inbox yet."}</p>
            </div>
          ) : (
            notifications.map((notification) => (
              <div
                key={notification.id}
                onClick={() => setExpandedId(expandedId === notification.id ? null : notification.id)}
                className={`p-4 sm:p-5 flex items-start justify-between gap-4 transition-colors cursor-pointer ${
                  notification.is_read ? "bg-surface opacity-80" : "bg-primary-soft/20 border-l-4 border-l-primary"
                }`}
              >
                <div className="space-y-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {!notification.is_read ? (
                      <span className="w-2 h-2 rounded-full bg-[#FF6A3D]" title="Unread" />
                    ) : null}
                    <Badge variant="outline" className="font-mono text-[10px] bg-surface">
                      {notification.event_type}
                    </Badge>
                    {notification.channel !== "IN_APP" ? (
                      <Badge variant="secondary" className="text-[10px]">{notification.channel}</Badge>
                    ) : null}
                    <span className="text-[11px] text-muted-foreground font-mono">
                      {new Date(notification.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className={`text-xs text-foreground leading-relaxed ${notification.is_read ? "" : "font-semibold"}`}>
                    {notification.message.length > 140 && expandedId !== notification.id
                      ? `${notification.message.slice(0, 140)}…`
                      : notification.message}
                  </p>
                </div>
                {!notification.is_read ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-primary font-semibold shrink-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      markRead.mutateAsync(notification.id);
                    }}
                  >
                    Mark read
                  </Button>
                ) : null}
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 ? (
        <div className="flex items-center justify-between px-2">
          <span className="text-xs text-muted-foreground font-mono">
            Page {page} of {totalPages} • {totalCount} total alerts
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="rounded-[8px] text-xs h-8"
              disabled={page <= 1}
              onClick={() => setSearchParams({ tab, page: String(page - 1) })}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="rounded-[8px] text-xs h-8"
              disabled={page >= totalPages}
              onClick={() => setSearchParams({ tab, page: String(page + 1) })}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
