import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { HybridBlackboard } from "./HybridBlackboard";

vi.mock("./MathEquationEditor",()=>({MathEquationEditor:()=> <div data-testid="mock-math-field"/>}));
afterEach(cleanup);
it("starts with prose and serializes alternating blocks",()=>{const onChange=vi.fn();render(<HybridBlackboard solution="" onChange={onChange}/>);expect(screen.getByLabelText("Texte 1")).toBeInTheDocument();fireEvent.change(screen.getByLabelText("Texte 1"),{target:{value:"On pose"}});expect(onChange).toHaveBeenLastCalledWith("On pose");fireEvent.click(screen.getByRole("button",{name:"+ Équation"}));expect(screen.getByTestId("mock-math-field")).toBeInTheDocument();});
it("loads legacy display math without causing a store update",()=>{const onChange=vi.fn();render(<HybridBlackboard solution={'Avant\n\n$$\nx^2=4\n$$\n\nAprès'} onChange={onChange}/>);expect(screen.getByLabelText("Texte 1")).toHaveValue("Avant");expect(screen.getByLabelText("Texte 3")).toHaveValue("Après");expect(onChange).not.toHaveBeenCalled();});
