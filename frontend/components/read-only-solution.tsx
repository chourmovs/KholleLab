import katex from "katex";
import {historySolutionContent} from "@/lib/solution-document";
import {MathContent} from "./math-content";

export function ReadOnlySolution({content}:{content:string}){
 const normalized=historySolutionContent(content);
 if(normalized.kind==="markdown")return <MathContent content={normalized.content}/>;
 return <div className="math-content unified-solution" dangerouslySetInnerHTML={{__html:katex.renderToString(`\\begin{gathered}${normalized.content}\\end{gathered}`,{displayMode:true,throwOnError:false,strict:"warn"})}}/>;
}
