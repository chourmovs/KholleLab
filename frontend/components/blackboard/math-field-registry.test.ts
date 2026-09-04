import { describe, expect, it, vi } from "vitest";
import { MathFieldRegistry } from "./MathFieldRegistry";
const field=()=>({focus:vi.fn(),insert:vi.fn(),getValue:vi.fn(()=>"")});
describe("MathFieldRegistry",()=>{
  it("switches the sole insertion target",()=>{const r=new MathFieldRegistry(),a=field(),b=field();r.register("a",a);r.register("b",b);r.activate("a");r.insertMathTemplate("=");r.activate("b");r.insertMathTemplate("\\sqrt{#0}");expect(a.insert).toHaveBeenCalledWith("=");expect(b.insert).toHaveBeenCalledWith("\\sqrt{#0}")});
  it("cannot retain a removed active field",()=>{const r=new MathFieldRegistry(),a=field();r.register("a",a);r.activate("a");r.unregister("a");expect(r.getActive()).toBeUndefined();r.insertMathTemplate("=");expect(a.insert).not.toHaveBeenCalled()});
});
