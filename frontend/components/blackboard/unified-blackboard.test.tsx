import {act,render,waitFor} from "@testing-library/react";
import {createRef} from "react";
import {expect,it,vi} from "vitest";
import {UnifiedBlackboard,type UnifiedBlackboardHandle} from "./UnifiedBlackboard";
const keyboard=Object.assign(new EventTarget(),{visible:false,layouts:[] as unknown[],alphabeticLayout:"",show:vi.fn(),hide:vi.fn()});
vi.mock("mathlive",()=>{Object.assign(window,{mathVirtualKeyboard:keyboard});if(!customElements.get("math-field"))customElements.define("math-field",class extends HTMLElement{value="";readOnly=false;defaultMode="text";smartMode=true;smartFence=true;letterShapeStyle="french";mathVirtualKeyboardPolicy="manual";placeholder=""});return {}});

it("renders exactly one continuous editable field and no block controls",async()=>{const {container}=render(<UnifiedBlackboard solution="" onChange={vi.fn()}/>);await waitFor(()=>expect(container.querySelectorAll("math-field")).toHaveLength(1));expect(container.querySelectorAll("textarea")).toHaveLength(0);expect(container.textContent).not.toMatch(/\+ Texte|\+ Équation/)});
it("uses the one global virtual keyboard and keeps focus",async()=>{const ref=createRef<UnifiedBlackboardHandle>();const {container}=render(<UnifiedBlackboard ref={ref} solution="" onChange={vi.fn()}/>);await waitFor(()=>expect(container.querySelector("math-field")).toBeTruthy());const field=container.querySelector("math-field")!;const focus=vi.spyOn(field as HTMLElement,"focus");const show=vi.spyOn(window.mathVirtualKeyboard,"show");act(()=>ref.current?.toggleKeyboard());expect(show).toHaveBeenCalledOnce();expect(focus).toHaveBeenCalledOnce()});
