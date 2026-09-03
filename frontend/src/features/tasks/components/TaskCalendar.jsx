import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarDays, ChevronLeft, ChevronRight, Clock3 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { taskPriorityName, taskStatusName } from "@/utils/taskMasterData";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const keyOf = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
const taskDate = (task) => {
  const date = task.due_date ? new Date(task.due_date) : null;
  return date && !Number.isNaN(date.getTime()) ? date : null;
};

function colorFor(task, overdue) {
  if (overdue) return "border-red-200 bg-red-50 text-red-700 hover:bg-red-100 dark:border-red-900 dark:bg-red-950/50 dark:text-red-300";
  const priority = taskPriorityName(task.priority)?.toLowerCase();
  if (priority === "high") return "border-blue-200 bg-blue-50 text-blue-800 hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950/50 dark:text-blue-200";
  if (priority === "medium") return "border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-200";
  return "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200";
}

export default function TaskCalendar({ tasks = [], isLoading = false }) {
  const today = new Date();
  const [month, setMonth] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [expanded, setExpanded] = useState({});
  const days = useMemo(() => {
    const first = new Date(month.getFullYear(), month.getMonth(), 1);
    const start = new Date(month.getFullYear(), month.getMonth(), 1 - ((first.getDay() + 6) % 7));
    return Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
  }, [month]);
  const grouped = useMemo(() => tasks.reduce((result, task) => {
    const date = taskDate(task);
    if (!date) return result;
    (result[keyOf(date)] ??= []).push(task);
    result[keyOf(date)].sort((a, b) => new Date(a.due_date) - new Date(b.due_date));
    return result;
  }, {}), [tasks]);
  const move = (amount) => {
    setMonth((current) => new Date(current.getFullYear(), current.getMonth() + amount, 1));
    setExpanded({});
  };

  return (
    <section className="overflow-hidden rounded-xl border bg-card shadow-sm" aria-label="Task calendar">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="grid size-9 place-items-center rounded-lg border bg-background text-primary"><CalendarDays className="size-4" /></span>
          <h2 className="text-lg font-semibold">{month.toLocaleDateString(undefined, { month: "long", year: "numeric" })}</h2>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="outline" size="sm" onClick={() => setMonth(new Date(today.getFullYear(), today.getMonth(), 1))}>Today</Button>
          <Button variant="outline" size="icon" onClick={() => move(-1)} aria-label="Previous month"><ChevronLeft /></Button>
          <Button variant="outline" size="icon" onClick={() => move(1)} aria-label="Next month"><ChevronRight /></Button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <div className="grid min-w-[760px] grid-cols-7 border-b bg-muted/30">
          {WEEKDAYS.map((day, index) => <div key={day} className={`px-2 py-2 text-center text-xs font-semibold uppercase tracking-wide ${index > 4 ? "text-red-500" : "text-muted-foreground"}`}>{day}</div>)}
        </div>
        <div className="grid min-w-[760px] grid-cols-7">
          {days.map((date) => {
            const key = keyOf(date);
            const items = grouped[key] ?? [];
            const shown = expanded[key] ? items : items.slice(0, 3);
            return (
              <div key={key} className={`min-h-32 border-b border-r p-1.5 ${date.getMonth() !== month.getMonth() ? "bg-muted/25 text-muted-foreground" : "bg-card"}`}>
                <div className="mb-1 flex h-6 items-center justify-between">
                  <span className={`grid size-6 place-items-center rounded-md text-xs font-medium ${key === keyOf(today) ? "bg-primary text-primary-foreground" : ""}`}>{date.getDate()}</span>
                  {items.length ? <span className="text-[10px] text-muted-foreground">{items.length}</span> : null}
                </div>
                <div className="space-y-1">
                  {shown.map((task) => {
                    const due = taskDate(task);
                    const completed = taskStatusName(task.status)?.toLowerCase() === "completed";
                    return <Link key={task.task_id} to={`/tasks/${task.task_id}`} title={task.task_title} className={`flex items-center gap-1 rounded-md border px-1.5 py-1 text-[11px] leading-tight transition-colors ${colorFor(task, due < today && !completed)} ${completed ? "opacity-60 line-through" : ""}`}><Clock3 className="size-3" /><span className="min-w-0 flex-1 truncate font-medium">{task.task_title}</span><span className="shrink-0 opacity-70">{due.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span></Link>;
                  })}
                  {items.length > 3 ? <button type="button" className="w-full rounded py-0.5 text-[11px] font-medium text-primary hover:bg-muted" onClick={() => setExpanded((value) => ({ ...value, [key]: !value[key] }))}>{expanded[key] ? "Show less" : `+${items.length - 3} more`}</button> : null}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      {isLoading ? <div className="border-t px-4 py-2 text-center text-xs text-muted-foreground">Loading calendar…</div> : null}
    </section>
  );
}
