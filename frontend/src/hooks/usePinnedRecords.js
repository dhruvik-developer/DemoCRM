import { useEffect, useState } from "react";

export function usePinnedRecords(storageKey) {
  const [pinnedIds, setPinnedIds] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(storageKey) || "[]").map(String);
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(pinnedIds));
  }, [pinnedIds, storageKey]);

  const isPinned = (id) => pinnedIds.includes(String(id));
  const togglePin = (id) => setPinnedIds((current) => {
    const value = String(id);
    return current.includes(value) ? current.filter((item) => item !== value) : [...current, value];
  });
  const pinnedFirst = (rows, getId) => [...rows].sort((a, b) => Number(isPinned(getId(b))) - Number(isPinned(getId(a))));

  return { pinnedIds, isPinned, togglePin, pinnedFirst };
}
