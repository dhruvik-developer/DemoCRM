import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getApiErrorMessage } from "@/utils/errors";
import { createRecordNote, getRecordNotes } from "./api";

const noteKey = (type, id) => ["record-notes", type, id];

export function useRecordNotes(type, id) {
  return useQuery({ queryKey: noteKey(type, id), queryFn: () => getRecordNotes(type, id), enabled: Boolean(type && id) });
}

export function useCreateRecordNote(type, id) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body) => createRecordNote({ entity_type: type, entity_id: id, body }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: noteKey(type, id) });
      toast.success("Note added.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });
}
