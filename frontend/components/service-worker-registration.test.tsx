import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  registerServiceWorker,
  ServiceWorkerRegistration,
} from "./service-worker-registration";

describe("service-worker registration", () => {
  it("registers the root service worker in production", () => {
    const register = vi.fn().mockResolvedValue(undefined);

    registerServiceWorker("production", { register } as unknown as ServiceWorkerContainer);

    expect(register).toHaveBeenCalledWith("/sw.js");
  });

  it("does not register outside production", () => {
    const register = vi.fn();

    registerServiceWorker("development", { register } as unknown as ServiceWorkerContainer);

    expect(register).not.toHaveBeenCalled();
  });

  it("mounts without rendering visible UI", () => {
    const { container } = render(<ServiceWorkerRegistration />);
    expect(container).toBeEmptyDOMElement();
  });
});
