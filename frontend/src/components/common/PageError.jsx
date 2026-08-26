// Inline error block for query failures. Message comes from
// normalizeApiError (attached by the axios interceptor as error.normalized).

import { Button } from "@/components/ui/button";

export default function PageError({ error, onRetry }) {
  const message =
    error?.normalized?.message || error?.message || "Something went wrong.";

  return (
    <div className="flex flex-col items-center justify-center gap-3 p-10 text-center">
      <p role="alert" className="text-sm font-medium text-destructive">
        {message}
      </p>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
