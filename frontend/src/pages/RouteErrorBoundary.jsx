// Route-level error boundary (react-router errorElement).
// Renders loader/action errors and render crashes with a retry.

import { Link, isRouteErrorResponse, useRouteError } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { getApiErrorMessage } from "@/utils/errors";

export default function RouteErrorBoundary() {
  const error = useRouteError();

  const status = isRouteErrorResponse(error) ? error.status : null;
  const message = isRouteErrorResponse(error)
    ? error.statusText || error.data
    : getApiErrorMessage(error);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-4xl font-semibold">{status ?? "Something went wrong"}</h1>
      <p className="max-w-md text-muted-foreground">
        {typeof message === "string" && message
          ? message
          : "An unexpected error occurred while rendering this page."}
      </p>
      <div className="flex gap-2">
        <Button onClick={() => window.location.reload()} variant="outline">
          Retry
        </Button>
        <Button asChild>
          <Link to="/">Go home</Link>
        </Button>
      </div>
    </div>
  );
}
