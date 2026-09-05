/** Shared visual primitives for KholleLab's classroom interface. */
export const tokens = {
  font: { sans: "var(--font-sans)", accent: "var(--font-accent)" },
  type: { display: "clamp(2rem, 4vw, 3.5rem)", h1: "1.5rem", h2: "1.2rem", h3: "1rem", body: ".9375rem", small: ".8125rem", caption: ".6875rem" },
  space: { 1: ".25rem", 2: ".5rem", 3: ".75rem", 4: "1rem", 5: "1.5rem", 6: "2rem" },
  radius: { small: "8px", medium: "14px", large: "20px", pill: "999px" },
  shadow: { panel: "0 18px 55px rgb(0 0 0 / 28%)", focus: "0 0 0 3px rgb(157 221 177 / 24%)" },
  color: { canvas: "#07100d", panel: "#101c18", board: "#10271f", ink: "#f3f0e7", muted: "#9aaba3", accent: "#a9d8b8", gold: "#e3c778", danger: "#e49580" },
} as const;

export type PanelVariant = "surface" | "blackboard" | "raised";
export type ButtonVariant = "primary" | "secondary" | "ghost" | "icon";
export type BadgeVariant = "neutral" | "success" | "warning" | "danger";
