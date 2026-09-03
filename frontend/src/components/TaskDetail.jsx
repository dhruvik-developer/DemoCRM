import { Link } from "react-router-dom";
import CallWorkspaceForm from "./CallWorkspaceForm";

const Detail = ({ label, children }) => <div><p className="text-xs uppercase text-gray-500">{label}</p><div className="mt-1 text-sm text-white">{children || "—"}</div></div>;

export default function TaskDetail({
  task = {},
  lead = {},
  stage = "New",
  nextStage = "Contacted",
  pipeline = "Sales Pipeline",
  onSaveDraft,
  onCompleteTask,
  onSubmitAndMove,
}) {
  const completed = String(task.status || "Pending").toLowerCase() === "completed";
  return (
    <main className="min-h-screen bg-black px-6 py-5 text-white">
      <div className="mx-auto max-w-4xl space-y-6">
        <nav className="text-xs text-gray-500">Overview / Tasks / <span className="text-white">{task.id || task.task_id || "—"}</span></nav>
        <header className="flex items-center gap-3"><h1 className="text-2xl font-semibold">{task.title || task.task_title || "Task"}</h1><span className={`rounded-full px-3 py-1 text-xs font-semibold ${completed ? "bg-green-900 text-green-200" : "bg-gray-700 text-gray-100"}`}>{completed ? "Completed" : "Pending"}</span></header>

        <section className="rounded-xl border border-gray-800 p-5"><h2 className="mb-5 font-semibold">Details</h2><div className="grid gap-5 md:grid-cols-3"><Detail label="Priority">{task.priority}</Detail><Detail label="Category">{task.category}</Detail><Detail label="Due date">{task.dueDate || task.due_date}</Detail><Detail label="Assigned to">{task.assignedTo || task.assigned_to}</Detail><Detail label="Lead"><Link className="text-blue-500 hover:underline" to={`/leads/${lead.id || task.lead || ""}`}>View lead</Link></Detail></div></section>
        <section className="rounded-xl border border-gray-800 p-5"><h2 className="mb-3 text-xs uppercase text-gray-500">Description</h2><p className="whitespace-pre-wrap text-sm">{task.description || "—"}</p></section>

        <CallWorkspaceForm lead={lead} stage={stage} nextStage={nextStage} pipeline={pipeline} onSaveDraft={onSaveDraft} onCompleteTask={onCompleteTask} onSubmitAndMove={onSubmitAndMove} />
      </div>
    </main>
  );
}
