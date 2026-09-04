export interface ProblemSource { type: string; name: string; year?: number; session?: string; url?: string }
export interface ProblemSummary { id:string; title:string; subtitle?:string; level:string; difficulty:number; estimatedMinutes?:number; year?:number; topics:string[]; source:ProblemSource }
export interface CoursePoint {title:string;summary:string;topics:string[]}
export interface VideoResource {title:string;provider:"youtube";url:string;author?:string;duration_minutes?:number}
export interface ProblemResources {course_points:CoursePoint[];videos:VideoResource[]}
export interface ProblemDetail extends ProblemSummary { statement:string;hintLevels:number[];resources?:ProblemResources }
export type AttemptStatus="draft"|"submitted";
export interface Attempt { id:string;problem_id:string;status:AttemptStatus;solution_markdown:string;revision:number;elapsed_seconds:number;started_at:string;updated_at:string;submitted_at:string|null }
export interface MathIssue {severity:"minor"|"major";category:string;description:string;candidate_excerpt:string|null}
export interface Evaluation {status:"running"|"completed"|"failed";verdict?:string;score?:number;max_score:number;confidence?:number;strategy_summary?:string;reference_relationship?:string;rubric?:{mathematical_correctness:number;rigor:number;clarity:number;efficiency:number};strengths:string[];issues:MathIssue[];missing_justifications:string[];key_feedback?:string;reference_method_summary?:string;suggested_improvement?:string;error_code?:string}
