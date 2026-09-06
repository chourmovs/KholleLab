import { describe, expect, it } from "vitest";
import { parseSolutionMarkdown, serializeSolutionDocument } from "./solution-document";

describe("solution document", () => {
  it.each(["Texte simple", "Comme $x>0$, ça va.", "Éléments ∈ ℝ et Unicode ≤", "$$ x+1"])("preserves prose: %s", (text) => {
    const document=parseSolutionMarkdown(text); expect(document.blocks).toHaveLength(1); expect(document.blocks[0]).toMatchObject({type:"text",content:text});
  });
  it("parses and canonically serializes several multiline equations", () => {
    const source="On considère x.\n\n$$\nx^2-1=\\frac{a}{b}\n$$\n\nPuis\n\n\\[\n\\int_0^1 x\\,dx\n\\]\n\nDonc.";
    const document=parseSolutionMarkdown(source); expect(document.blocks.map(block=>block.type)).toEqual(["text","math","text","math","text"]);
    expect(document.blocks[1]).toMatchObject({latex:"x^2-1=\\frac{a}{b}"});
    const roundTrip=parseSolutionMarkdown(serializeSolutionDocument(document));
    expect(roundTrip.blocks.map(block=>block.type==="text"?block.content:block.latex)).toEqual(document.blocks.map(block=>block.type==="text"?block.content:block.latex));
  });
  it("represents an empty solution as one text block",()=>expect(parseSolutionMarkdown("").blocks).toMatchObject([{type:"text",content:""}]));
  it.each(["$$\nx+y\n\\]","\\[\nx+y\n$$","Texte $x$ puis $y$", "avant\n\n$$ malformed\n\naprès"])("keeps mixed, inline, and malformed math as prose",source=>expect(parseSolutionMarkdown(source).blocks).toMatchObject([{type:"text",content:source}]));
  it("round-trips an empty display-math block",()=>expect(serializeSolutionDocument(parseSolutionMarkdown("$$\n\n$$"))).toBe("$$\n\n$$"));
});
