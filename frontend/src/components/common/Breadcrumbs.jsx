import { Link, useLocation } from "react-router-dom";

const LABELS = { leads: "Leads", customers: "Customers", tasks: "Tasks", quotations: "Quotations", admin: "Admin" };

export default function Breadcrumbs() {
  const { pathname } = useLocation();
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length <= 1) return null;
  return (
    <nav className="flex items-center gap-1 text-xs text-muted-foreground" aria-label="Breadcrumbs">
      <Link to="/" className="hover:underline">Overview</Link>
      {parts.map((p, i) => {
        const to = "/" + parts.slice(0, i + 1).join("/");
        const isLast = i === parts.length - 1;
        const label = LABELS[p] ?? p.replace(/-/g, " ");
        return (
          <span key={to} className="flex items-center gap-1">
            <span>/</span>
            {isLast ? <span className="font-medium text-foreground">{label}</span> : <Link to={to} className="hover:underline">{label}</Link>}
          </span>
        );
      })}
    </nav>
  );
}
