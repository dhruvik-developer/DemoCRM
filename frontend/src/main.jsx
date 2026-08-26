import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";

import App from "./App";
import { queryClient } from "./api/queryClient";
import "./index.css";

// MSW is opt-in for component work while the backend/CORS fixes land
// (implementation plan Phase 1). Real backend is the default.
async function enableMocking() {
  if (import.meta.env.VITE_ENABLE_MOCKS !== "true") return;
  const { worker } = await import("./mocks/browser");
  await worker.start({ onUnhandledRequest: "bypass" });
}

enableMocking().then(() => {
  createRoot(document.getElementById("root")).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </StrictMode>,
  );
});
