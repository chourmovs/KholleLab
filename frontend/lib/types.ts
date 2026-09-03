export interface ProblemSource { type: string; name: string; year?: number; session?: string; url?: string }
export interface ProblemSummary { id:string; title:string; subtitle?:string; level:string; difficulty:number; estimatedMinutes?:number; year?:number; topics:string[]; source:ProblemSource }
export interface ProblemDetail extends ProblemSummary { statement:string; hintLevels:number[] }
export type AttemptStatus="draft"|"submitted";
export interface Attempt { id:string;problem_id:string;status:AttemptStatus;solution_markdown:string;revision:number;elapsed_seconds:number;started_at:string;updated_at:string;submitted_at:string|null }
