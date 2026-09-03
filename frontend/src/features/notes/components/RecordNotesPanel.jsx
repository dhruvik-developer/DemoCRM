import { useState } from "react";
import { MessageSquareText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useCreateRecordNote, useRecordNotes } from "../hooks";

export default function RecordNotesPanel({ record, onClose }) {
  const [body, setBody] = useState("");
  const notesQuery = useRecordNotes(record?.type, record?.id);
  const createNote = useCreateRecordNote(record?.type, record?.id);
  const notes = notesQuery.data ?? [];

  const submit = async (event) => {
    event.preventDefault();
    if (!body.trim()) return;
    await createNote.mutateAsync(body.trim());
    setBody("");
  };

  return (
    <Dialog open={Boolean(record)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="left-auto right-0 top-0 h-dvh w-full max-w-xl translate-x-0 translate-y-0 content-start gap-0 rounded-none p-0 sm:max-w-xl" showCloseButton>
        <DialogHeader className="border-b px-6 py-5">
          <DialogTitle className="flex items-center gap-2"><MessageSquareText className="size-5" /> Notes <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{notes.length}</span></DialogTitle>
          <DialogDescription>{record?.title}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex gap-2 border-b p-5">
          <Textarea value={body} onChange={(event) => setBody(event.target.value)} placeholder="Add a note" rows={2} maxLength={5000} />
          <Button type="submit" disabled={!body.trim() || createNote.isPending}>{createNote.isPending ? "Adding…" : "Add"}</Button>
        </form>
        <div className="max-h-[calc(100dvh-190px)] space-y-3 overflow-y-auto p-5">
          {notesQuery.isLoading ? <p className="text-sm text-muted-foreground">Loading notes…</p> : null}
          {notesQuery.isError ? <p className="text-sm text-destructive">Could not load notes.</p> : null}
          {!notesQuery.isLoading && !notes.length ? <p className="py-10 text-center text-sm text-muted-foreground">No notes yet. Add the first note above.</p> : null}
          {notes.map((note) => (
            <article key={note.note_id} className="rounded-xl border bg-card p-4">
              <div className="mb-2 flex items-center justify-between gap-3 text-xs text-muted-foreground"><strong className="text-foreground">{note.author_name}</strong><time>{new Date(note.created_at).toLocaleString()}</time></div>
              <p className="whitespace-pre-wrap text-sm">{note.body}</p>
            </article>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
