import {render} from "@testing-library/react";
import {describe,expect,it} from "vitest";
import {MathContent} from "../math-content";

describe("MathContent",()=>{
  it("keeps the exact two-inline-formula statement in one paragraph",()=>{const{container}=render(<MathContent content="Pour $f(x)=-2x+7$, déterminer l’antécédent de $1$."/>);const paragraphs=container.querySelectorAll(":scope > .math-content > p");expect(paragraphs).toHaveLength(1);expect(paragraphs[0].querySelectorAll(".math-inline")).toHaveLength(2);expect(paragraphs[0].textContent).toContain("Pour");expect(paragraphs[0].textContent).toContain("déterminer l’antécédent de");expect(paragraphs[0].textContent?.endsWith(".")).toBe(true);expect([...paragraphs].some(paragraph=>paragraph.textContent===".")).toBe(false)});
  it("keeps one inline derivative formula with its prose",()=>{const{container}=render(<MathContent content="Calculer la dérivée de $f(x)=3x^2-4x+1$."/>);const paragraphs=container.querySelectorAll(":scope > .math-content > p");expect(paragraphs).toHaveLength(1);expect(paragraphs[0].querySelectorAll(".math-inline")).toHaveLength(1);expect(paragraphs[0].textContent?.endsWith(".")).toBe(true)});
  it("renders display mathematics between separate prose paragraphs",()=>{const{container}=render(<MathContent content={'Première étape.\n\n$$x^2+1=0$$\n\nConclusion.'}/>);const content=container.querySelector(".math-content")!;expect(content.children).toHaveLength(3);expect(content.children[0].tagName).toBe("P");expect(content.children[1]).toHaveClass("math-display");expect(content.children[2].tagName).toBe("P");expect(content.querySelectorAll(":scope > p")).toHaveLength(2)});
});
