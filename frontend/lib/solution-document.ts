export interface TextBlock { id: string; type: "text"; content: string }
export interface MathBlock { id: string; type: "math"; latex: string }
export type SolutionBlock = TextBlock | MathBlock;
export interface SolutionDocument { version: 1; blocks: SolutionBlock[] }

let nextId = 0;
export const solutionBlockId = () => `solution-block-${Date.now().toString(36)}-${nextId++}`;
export const emptySolutionDocument = (): SolutionDocument => ({
  version: 1,
  blocks: [{ id: solutionBlockId(), type: "text", content: "" }],
});

// Only stand-alone display delimiters become editor blocks. Inline and malformed
// delimiters deliberately stay prose so opening a legacy copy is lossless.
const DISPLAY_MATH = /(?:^|\n)[ \t]*(\$\$|\\\[)[ \t]*\n([\s\S]*?)\n[ \t]*(?:\$\$|\\\])[ \t]*(?=\n|$)/g;

export function parseSolutionMarkdown(markdown: string): SolutionDocument {
  if (!markdown) return emptySolutionDocument();
  const blocks: SolutionBlock[] = [];
  let cursor = 0;
  for (const match of markdown.matchAll(DISPLAY_MATH)) {
    const index = match.index ?? 0;
    const leadingNewline = match[0].startsWith("\n") ? 1 : 0;
    const text = markdown.slice(cursor, index + leadingNewline).replace(/\n{2}$/, "");
    if (text) blocks.push({ id: solutionBlockId(), type: "text", content: text });
    blocks.push({ id: solutionBlockId(), type: "math", latex: match[2] });
    cursor = index + match[0].length;
    while (markdown[cursor] === "\n" && markdown[cursor + 1] === "\n") cursor++;
  }
  const tail = markdown.slice(cursor).replace(/^\n{1,2}/, "");
  if (tail) blocks.push({ id: solutionBlockId(), type: "text", content: tail });
  return blocks.length ? { version: 1, blocks } : { version: 1, blocks: [{ id: solutionBlockId(), type: "text", content: markdown }] };
}

export function serializeSolutionDocument(document: SolutionDocument): string {
  return document.blocks.map((block) => block.type === "math" ? `$$\n${block.latex}\n$$` : block.content).join("\n\n");
}
