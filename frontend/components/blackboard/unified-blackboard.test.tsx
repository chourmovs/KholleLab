import {act,render,waitFor} from "@testing-library/react";
import {beforeEach,expect,it,vi} from "vitest";
import {createRef} from "react";
import {UnifiedBlackboard,type UnifiedBlackboardHandle} from "./UnifiedBlackboard";

const keyboard=Object.assign(new EventTarget(),{
 visible:false,layouts:[] as unknown[],alphabeticLayout:"",
 show:vi.fn(function(this:typeof keyboard){this.visible=true;this.dispatchEvent(new Event("virtual-keyboard-toggle"))}),
 hide:vi.fn(function(this:typeof keyboard){this.visible=false;this.dispatchEvent(new Event("virtual-keyboard-toggle"))}),
 setKeycap:vi.fn(),
});

vi.mock("mathlive",()=>{
 Object.assign(window,{mathVirtualKeyboard:keyboard});
 if(!customElements.get("math-field"))customElements.define("math-field",class extends HTMLElement{
  value="";position=0;lastOffset=20;readOnly=false;defaultMode="text";smartMode=true;smartFence=true;letterShapeStyle="french";mathVirtualKeyboardPolicy="manual";placeholder="";
  hasFocus=vi.fn(()=>false);
  constructor(){super();const shadow=this.attachShadow({mode:"open"});const sink=document.createElement("span");sink.setAttribute("part","keyboard-sink");shadow.append(sink)}
  setValue=vi.fn((value:string)=>{this.value=value});
  insert=vi.fn((value:string)=>{this.value+=value;this.dispatchEvent(new Event("input"));return true});
  executeCommand=vi.fn((command:string)=>{if(command==="addRowAfter"){this.value=this.value.replace(/}$/,"\\\\ }");this.dispatchEvent(new Event("input"))}return true});
 });
 return {};
});

beforeEach(()=>{keyboard.visible=false;keyboard.show.mockClear();keyboard.hide.mockClear();keyboard.setKeycap.mockClear()});

it("renders one editor configured for native text input without opening the scientific keyboard",async()=>{
 const {container}=render(<UnifiedBlackboard solution="" onChange={vi.fn()}/>);
 await waitFor(()=>expect(container.querySelector("math-field")).toBeTruthy());
 const field=container.querySelector("math-field") as HTMLElement&{defaultMode:string;smartMode:boolean;smartFence:boolean;mathVirtualKeyboardPolicy:string};
 expect(container.querySelectorAll("math-field")).toHaveLength(1);expect(container.querySelectorAll("textarea")).toHaveLength(0);
 expect(field).toHaveAttribute("aria-label","Tableau de résolution");expect(field.defaultMode).toBe("text");expect(field.smartMode).toBe(true);expect(field.smartFence).toBe(true);expect(field.mathVirtualKeyboardPolicy).toBe("manual");
 expect(field.shadowRoot?.querySelector("[part=keyboard-sink]")).toHaveAttribute("inputmode","text");expect(keyboard.show).not.toHaveBeenCalled();expect(container.textContent).not.toContain("\\displaylines");
});

it("shows and hides the scientific keyboard on the same focused editor without moving its caret or changing content",async()=>{
 const ref=createRef<UnifiedBlackboardHandle>(),onChange=vi.fn();const {container}=render(<UnifiedBlackboard ref={ref} solution="abcDEF" onChange={onChange}/>);
 await waitFor(()=>expect(container.querySelector("math-field")).toBeTruthy());
 const field=container.querySelector("math-field") as HTMLElement&{position:number};field.position=7;const focus=vi.spyOn(field,"focus");
 act(()=>ref.current?.toggleKeyboard());expect(keyboard.show).toHaveBeenCalledOnce();expect(focus).toHaveBeenCalledOnce();expect(field.position).toBe(7);expect(onChange).not.toHaveBeenCalled();expect(field.shadowRoot?.querySelector("[part=keyboard-sink]")).toHaveAttribute("inputmode","none");
 act(()=>ref.current?.toggleKeyboard());expect(keyboard.hide).toHaveBeenCalledOnce();expect(focus).toHaveBeenCalledOnce();expect(field.position).toBe(7);expect(onChange).not.toHaveBeenCalled();expect(field.shadowRoot?.querySelector("[part=keyboard-sink]")).toHaveAttribute("inputmode","text");
});

it("focuses an editable field once after a touch places the caret",async()=>{
 const {container}=render(<UnifiedBlackboard solution="abc" onChange={vi.fn()}/>);await waitFor(()=>expect(container.querySelector("math-field")).toBeTruthy());
 const field=container.querySelector("math-field") as HTMLElement&{position:number;hasFocus:ReturnType<typeof vi.fn>};field.position=4;const focus=vi.spyOn(field,"focus");field.dispatchEvent(new PointerEvent("pointerup"));expect(focus).toHaveBeenCalledOnce();expect(field.position).toBe(4);field.hasFocus.mockReturnValue(true);field.dispatchEvent(new PointerEvent("pointerup"));expect(focus).toHaveBeenCalledOnce();expect(field.position).toBe(4);
});

it("propagates normal French/mathematical input through the unified solution",async()=>{
 const onChange=vi.fn();const {container}=render(<UnifiedBlackboard solution="" onChange={onChange}/>);await waitFor(()=>expect(container.querySelector("math-field")).toBeTruthy());
 const field=container.querySelector("math-field") as HTMLElement&{value:string};field.value="\\displaylines{\\text{Soit f(x)=x, donc é à.}}";field.dispatchEvent(new InputEvent("input",{data:"."}));
 expect(onChange).toHaveBeenCalledOnce();expect(onChange).toHaveBeenLastCalledWith("\\text{Soit f(x)=x, donc é à.}");
});

it("publishes only the final committed value of an IME composition",async()=>{
 const onChange=vi.fn();const {container}=render(<UnifiedBlackboard solution="" onChange={onChange}/>);await waitFor(()=>expect(container.querySelector("math-field")).toBeTruthy());
 const field=container.querySelector("math-field") as HTMLElement&{value:string};field.dispatchEvent(new CompositionEvent("compositionstart",{data:""}));field.value="\\displaylines{\\text{e}}";field.dispatchEvent(new InputEvent("input",{data:"e",inputType:"insertCompositionText"}));field.value="\\displaylines{\\text{é}}";field.dispatchEvent(new InputEvent("input",{data:"é",inputType:"insertCompositionText"}));expect(onChange).not.toHaveBeenCalled();field.dispatchEvent(new CompositionEvent("compositionend",{data:"é"}));
 expect(onChange).toHaveBeenCalledOnce();expect(onChange).toHaveBeenLastCalledWith("\\text{é}");
});

it("creates a row for desktop Enter and Android insertParagraph",async()=>{
 const {container}=render(<UnifiedBlackboard solution="" onChange={vi.fn()}/>);await waitFor(()=>expect(container.querySelector("math-field")).toBeTruthy());
 const field=container.querySelector("math-field") as HTMLElement&{executeCommand:ReturnType<typeof vi.fn>};const enter=new KeyboardEvent("keydown",{key:"Enter",cancelable:true});field.dispatchEvent(enter);expect(enter.defaultPrevented).toBe(true);expect(field.executeCommand).toHaveBeenCalledWith("addRowAfter");
 const sink=field.shadowRoot!.querySelector("[part=keyboard-sink]")!;const imeEnter=new InputEvent("beforeinput",{inputType:"insertParagraph",cancelable:true,bubbles:true});sink.dispatchEvent(imeEnter);expect(imeEnter.defaultPrevented).toBe(true);expect(field.executeCommand).toHaveBeenCalledTimes(2);
 field.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",ctrlKey:true,cancelable:true}));expect(field.executeCommand).toHaveBeenCalledTimes(2);
});

it("preserves native plus input after the scientific keyboard closes",async()=>{
 const ref=createRef<UnifiedBlackboardHandle>();const {container}=render(<UnifiedBlackboard ref={ref} solution="x" onChange={vi.fn()}/>);await waitFor(()=>expect(container.querySelector("math-field")).toBeTruthy());
 const field=container.querySelector("math-field") as HTMLElement&{insert:ReturnType<typeof vi.fn>};act(()=>{ref.current?.toggleKeyboard();ref.current?.toggleKeyboard()});
 const plus=new KeyboardEvent("keydown",{key:"+",cancelable:true});field.dispatchEvent(plus);expect(plus.defaultPrevented).toBe(true);expect(field.insert).toHaveBeenCalledWith("+",{mode:"math",selectionMode:"after",focus:true});
});

it("exposes addRowAfter on the scientific return keys",async()=>{
 render(<UnifiedBlackboard solution="" onChange={vi.fn()}/>);await waitFor(()=>expect(keyboard.setKeycap).toHaveBeenCalled());
 expect(keyboard.setKeycap).toHaveBeenCalledWith("[return]",expect.objectContaining({label:"↵",command:"addRowAfter",class:"action"}));const basic=keyboard.layouts[0] as {rows:unknown[][]};expect(basic.rows.flat()).toContainEqual(expect.objectContaining({label:"↵",command:"addRowAfter"}));
});

it("keeps a submitted board read-only and cannot open either input path",async()=>{
 const ref=createRef<UnifiedBlackboardHandle>();const {container}=render(<UnifiedBlackboard ref={ref} solution="abc" onChange={vi.fn()} readOnly/>);await waitFor(()=>expect(container.querySelector("math-field")).toBeTruthy());
 const field=container.querySelector("math-field") as HTMLElement&{readOnly:boolean;executeCommand:ReturnType<typeof vi.fn>};expect(field.readOnly).toBe(true);expect(field.shadowRoot?.querySelector("[part=keyboard-sink]")).toHaveAttribute("inputmode","none");act(()=>{ref.current?.toggleKeyboard();ref.current?.insertLineBreak()});expect(keyboard.show).not.toHaveBeenCalled();expect(field.executeCommand).not.toHaveBeenCalled();
});
