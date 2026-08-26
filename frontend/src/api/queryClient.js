// Shared TanStack Query client — imported by main.jsx and by mutation hooks
// that need cache invalidation outside React components.

import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
