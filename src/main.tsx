import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";
import { initTheme } from "./utils/theme";
import { purgeLegacyBrowserStorage } from "./services/api";

// Apply the persisted light/dark preference before the first paint.
initTheme();

// Business data is never read from browser storage. Remove anything an older
// build may have cached there (AI insight / chat transcript) before rendering.
const removedKeys = purgeLegacyBrowserStorage();
if (removedKeys.length) console.info("ClimaCred: removed stale browser storage", removedKeys);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
