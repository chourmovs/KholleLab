"use client";

import { useEffect } from "react";

export function registerServiceWorker(
  environment = process.env.NODE_ENV,
  serviceWorker = typeof navigator === "undefined" ? undefined : navigator.serviceWorker,
) {
  if (environment !== "production" || !serviceWorker) return;

  void serviceWorker.register("/sw.js").catch(() => {
    // Offline support is an enhancement; registration failure must not affect the app.
  });
}

export function ServiceWorkerRegistration() {
  useEffect(() => registerServiceWorker(), []);
  return null;
}
