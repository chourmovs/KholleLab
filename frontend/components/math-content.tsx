import type {ReactNode} from "react";
import katex from "katex";

const DISPLAY_RE=/(\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$)/g;
const INLINE_RE=/(\\\([\s\S]*?\\\)|\$[^$\n]+\$)/g;

function formula(token:string,displayMode:boolean,key:string){const edge=token.startsWith("$")?(displayMode?2:1):2;return <span key={key} className={displayMode?"math-display":"math-inline"} dangerouslySetInnerHTML={{__html:katex.renderToString(token.slice(edge,-edge),{displayMode,throwOnError:false,strict:"warn"})}}/>}
function renderInline(text:string,key:string):ReactNode[]{return text.split(INLINE_RE).filter(Boolean).map((token,index)=>token.startsWith("\\(")||token.startsWith("$")?formula(token,false,`${key}-${index}`):token)}
export function MathContent({content}:{content:string}){if(content.startsWith("\\text{"))return <div className="math-content unified-solution" dangerouslySetInnerHTML={{__html:katex.renderToString(content,{displayMode:true,throwOnError:false,strict:"warn"})}}/>;const blocks=content.split(DISPLAY_RE).filter(Boolean);return <div className="math-content">{blocks.flatMap((block,index)=>{if(block.startsWith("\\[")||block.startsWith("$$"))return [formula(block,true,`display-${index}`)];return block.split(/\n\s*\n+/).map(paragraph=>paragraph.trim()).filter(Boolean).map((paragraph,paragraphIndex)=><p key={`${index}-${paragraphIndex}`}>{renderInline(paragraph,`${index}-${paragraphIndex}`)}</p>)})}</div>}
