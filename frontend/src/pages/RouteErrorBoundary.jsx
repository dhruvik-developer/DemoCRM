import { useRouteError, isRouteErrorResponse } from "react-router-dom";

import { Button } from "@/components/ui/button";

export default function RouteErrorBoundary() {
  const error = useRouteError();

  const title = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : "Something went wrong";
  const message = isRouteErrorResponse(error)
    ? error.data
    : error?.message || "An unexpected error occurred while rendering this page.";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-4xl font-semibold">{title}</h1>
      <p className="text-muted-foreground">{message}</p>
      <Button asChild variant="outline">
        <a href="/">Go home</a>
      </Button>
    </div>
  );
}
