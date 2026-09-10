import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import OfflinePage from "./page";

describe("offline route", () => {
  it("renders the branded French fallback and retry action", () => {
    render(<OfflinePage />);

    expect(screen.getByRole("img", { name: "KHOLLELAB" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Service temporairement indisponible" })).toBeInTheDocument();
    expect(screen.getByText(/ne parvient pas à joindre le serveur/i)).toBeInTheDocument();
    const retry = screen.getByRole("button", { name: "Réessayer" });
    expect(retry).toHaveAttribute("type", "submit");
    expect(retry.closest("form")).toHaveAttribute("action", "/");
  });
});
