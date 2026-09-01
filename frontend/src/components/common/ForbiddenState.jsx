import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function ForbiddenState() {
  return (
    <Card className="rounded-xl m-6">
      <CardContent className="p-8 text-center">
        <p className="text-sm text-destructive">You do not have permission to perform this action.</p>
        <p className="text-xs text-muted-foreground mt-1">Ask an admin to grant your role the required permission.</p>
        <Button asChild variant="outline" size="sm" className="mt-3"><Link to="/">Back to overview</Link></Button>
      </CardContent>
    </Card>
  );
}
