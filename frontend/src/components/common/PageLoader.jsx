// Full-screen loader used while TanStack Query / auth state initialize.

export default function PageLoader({ label = "Loading…" }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-10">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}
