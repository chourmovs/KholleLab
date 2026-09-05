export interface ProblemSource { type: string; name: string; year?: number; session?: string; url?: string }
export interface Curriculum {level:string;difficulty:number}
export interface ProblemSummary { id:string; title:string; subtitle?:string; curriculum:Curriculum; estimatedMinutes?:number; year?:number; topics:string[]; source:ProblemSource }
export interface CoursePoint {title:string;summary:string;topics:string[]}
export interface VideoResource {title:string;provider:"youtube";url:string;author?:string;duration_minutes?:number}
export interface ProblemResources {course_points:CoursePoint[];videos:VideoResource[]}
export interface ProblemDetail extends ProblemSummary { statement:string;hintLevels:number[];prerequisites:string[];skills:string[];resources?:ProblemResources }
export interface CurriculumMetadata {levels:{id:string;label:string}[];difficulties:{id:number;label:string}[]}
export interface SelectionResult {problem:ProblemDetail|null;requested_level:string;requested_difficulty?:number;actual_difficulty?:number;fallback_used:boolean}
export type AttemptStatus="draft"|"submitted";
export interface Attempt { id:string;problem_id:string;status:AttemptStatus;solution_markdown:string;revision:number;elapsed_seconds:number;started_at:string;updated_at:string;submitted_at:string|null }
export interface MathIssue {severity:"minor"|"major";category:string;description:string;candidate_excerpt:string|null}
export type EvaluationStage="queued"|"candidate_audit"|"adjudication"|"finalizing"|"completed"|"failed";
export interface Evaluation {provider?:string;model?:string;model_family?:string;inference_backend?:string;status:"running"|"completed"|"failed";stage:EvaluationStage;progress:number;elapsed_ms?:number;verdict?:string;score?:number;max_score:number;confidence?:number;strategy_summary?:string;reference_relationship?:string;rubric?:{mathematical_correctness:number;rigor:number;clarity:number;efficiency:number};strengths:string[];issues:MathIssue[];missing_justifications:string[];key_feedback?:string;reference_method_summary?:string;suggested_improvement?:string;error_code?:string}
