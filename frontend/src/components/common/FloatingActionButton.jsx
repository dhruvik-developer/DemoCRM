import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, UserPlus, CheckSquare, FileText, Search } from "lucide-react";

export default function FloatingActionButton({ onOpenCommand }) {
  const [open, setOpen] = useState(false);

  const actions = [
    { label: "New Lead", icon: UserPlus, to: "/leads/new", color: "bg-[#FF6A3D] text-white hover:bg-[#E0532A]" },
    { label: "New Task", icon: CheckSquare, to: "/tasks/new", color: "bg-[#113D37] text-white hover:bg-[#0A2B26]" },
    { label: "New Quotation", icon: FileText, to: "/quotations/new", color: "bg-[#2E8B57] text-white hover:bg-[#247045]" },
  ];

  return (
    <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end gap-2.5">
      {/* Speed Dial Menu Items */}
      {open && (
        <div className="flex flex-col items-end gap-2 mb-1 animate-in fade-in slide-in-from-bottom-3 duration-200">
          {actions.map((action) => (
            <Link
              key={action.to}
              to={action.to}
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 group cursor-pointer"
            >
              <span className="rounded-md bg-surface border border-border px-2 py-1 text-xs font-semibold text-foreground shadow-sm opacity-90 group-hover:opacity-100 transition-opacity">
                {action.label}
              </span>
              <span className={`w-10 h-10 rounded-full flex items-center justify-center shadow-lg transition-transform group-hover:scale-110 ${action.color}`}>
                <action.icon className="h-4 w-4" />
              </span>
            </Link>
          ))}
          {onOpenCommand && (
            <button
              onClick={() => {
                setOpen(false);
                onOpenCommand();
              }}
              className="flex items-center gap-2.5 group cursor-pointer"
            >
              <span className="rounded-md bg-surface border border-border px-2 py-1 text-xs font-semibold text-foreground shadow-sm opacity-90 group-hover:opacity-100 transition-opacity">
                Search (⌘K)
              </span>
              <span className="w-10 h-10 rounded-full bg-surface border border-border text-foreground flex items-center justify-center shadow-lg transition-transform group-hover:scale-110 hover:bg-muted">
                <Search className="h-4 w-4 text-primary" />
              </span>
            </button>
          )}
        </div>
      )}

      {/* Main Trigger Button */}
      <button
        onClick={() => setOpen((prev) => !prev)}
        aria-label="Quick Actions Menu"
        className={`w-12 h-12 rounded-full flex items-center justify-center shadow-xl transition-all duration-300 cursor-pointer ${
          open
            ? "bg-[#113D37] text-white rotate-45 scale-105"
            : "bg-[#FF6A3D] text-[#2B1206] hover:bg-[#E0532A] hover:text-white hover:scale-105"
        }`}
      >
        <Plus className="h-6 w-6 stroke-[2.5]" />
      </button>
    </div>
  );
}
