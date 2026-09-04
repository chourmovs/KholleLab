import { render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { MathEquationEditor } from "./MathEquationEditor";

vi.mock("mathlive",()=>{if(!customElements.get("math-field"))customElements.define("math-field",class extends HTMLElement{value="";readOnly=false;mathVirtualKeyboardPolicy="manual";executeCommand(){} });return {}});
it("sets a value and accessible label on its custom element",async()=>{render(<MathEquationEditor value="x^2" readOnly onChange={vi.fn()} label="Formule"/>);await waitFor(()=>expect(screen.getByLabelText("Formule")).toBeInTheDocument());expect((screen.getByLabelText("Formule") as HTMLElement & {value:string}).value).toBe("x^2");});
