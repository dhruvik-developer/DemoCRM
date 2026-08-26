// Empty state with optional call-to-action, used by list pages.

import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function EmptyState({ title, description, ctaLabel, ctaTo }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 p-12 text-center">
      <h3 className="text-lg font-medium">{title}</h3>
      {description ? (
        <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      ) : null}
      {ctaLabel && ctaTo ? (
        <Button asChild className="mt-3">
          <Link to={ctaTo}>{ctaLabel}</Link>
        </Button>
      ) : null}
    </div>
  );
}
