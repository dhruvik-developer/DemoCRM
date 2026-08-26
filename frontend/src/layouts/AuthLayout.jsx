// Centered card layout for auth screens (implementation plan Phase 5).

import { Card, CardContent } from "@/components/ui/card";

export default function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <Card className="w-full max-w-md">
        <CardContent className="flex flex-col gap-6 pt-6">
          <div className="flex flex-col gap-1 text-center">
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            {subtitle ? (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            ) : null}
          </div>
          {children}
        </CardContent>
      </Card>
    </div>
  );
}
