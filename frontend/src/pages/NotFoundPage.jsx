import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-4xl font-semibold">404</h1>
      <p className="text-muted-foreground">This page does not exist.</p>
      <Button asChild variant="outline">
        <a href="/">Go home</a>
      </Button>
    </div>
  );
}
