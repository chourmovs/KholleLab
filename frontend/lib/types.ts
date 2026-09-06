export interface ProblemSource { type: string; name: string; year?: number; session?: string; url?: string }
export interface Curriculum {level:string;difficulty:number}
export interface ProblemSummary { id:string; title:string; subtitle?:string; curriculum:Curriculum; estimatedMinutes?:number; year?:number; topics:string[]; source:ProblemSource }
export interface CoursePoint {title:string;summary:string;topics:string[]}
export type ResourceType="course"|"example"|"video";
export interface ResourceMetadata {id:string;type:ResourceType;title:string;curriculum_levels:string[];topics:string[];prerequisites:string[];skills:string[];tags:string[];priority:number}
export interface CourseResource extends ResourceMetadata {type:"course";summary:string;content:string}
export interface ExampleResource extends ResourceMetadata {type:"example";statement:string;solution:string}
export interface VideoResource extends ResourceMetadata {type:"video";provider:"youtube";url:string;author:string;duration_minutes:number}
export type PedagogicalResource=CourseResource|ExampleResource|VideoResource;
export interface ResolvedResourcesResponse {problem_id:string;resources:PedagogicalResource[]}
export interface LegacyVideoResource {title:string;provider:"youtube";url:string;author?:string;duration_minutes?:number}
export interface ProblemResources {course_points:CoursePoint[];videos:LegacyVideoResource[]}
export interface ProblemDetail extends ProblemSummary { statement:string;hintLevels:number[];prerequisites:string[];skills:string[];resources?:ProblemResources }
export interface CurriculumMetadata {levels:{id:string;label:string}[];difficulties:{id:number;label:string}[]}
export interface SelectionResult {problem:ProblemDetail|null;requested_level:string;requested_difficulty?:number;actual_difficulty?:number;fallback_used:boolean}
export type AttemptStatus="draft"|"submitted";
export interface Attempt { id:string;problem_id:string;status:AttemptStatus;solution_markdown:string;revision:number;elapsed_seconds:number;started_at:string;updated_at:string;submitted_at:string|null }
export interface MathIssue {severity:"minor"|"major";category:string;description:string;candidate_excerpt:string|null}
export type EvaluationStage="queued"|"candidate_audit"|"adjudication"|"finalizing"|"completed"|"failed";
export interface Evaluation {provider?:string;model?:string;model_family?:string;inference_backend?:string;status:"running"|"completed"|"failed";stage:EvaluationStage;progress:number;elapsed_ms?:number;verdict?:string;score?:number;max_score:number;confidence?:number;strategy_summary?:string;reference_relationship?:string;rubric?:{mathematical_correctness:number;rigor:number;clarity:number;efficiency:number};strengths:string[];issues:MathIssue[];missing_justifications:string[];key_feedback?:string;reference_method_summary?:string;suggested_improvement?:string;error_code?:string}
export type TutorTrigger="meaningful_progress"|"stalled"|"ask_hint"|"i_am_stuck";
export type ResourceNeed="none"|"course_gap"|"method_gap"|"example_helpful";
export interface TutorResourceRecommendation {id:string;type:ResourceType;title:string;need:ResourceNeed}
export interface TutorAssessment {status:"completed";assessment_id:string;revision:number;student_state:string;intervention_needed:boolean;intervention_type:string;intervention:string|null;confidence:number;effective_help_level:number;provider:string;model:string;backend:string;resource_recommendation?:TutorResourceRecommendation|null}
export type LearningSessionStatus="active"|"completed"|"abandoned";
export interface LearningSessionSummary {session_id:string;problem_id:string;problem_title:string;status:LearningSessionStatus;created_at:string;updated_at:string;started_at:string;completed_at:string|null;duration_seconds:number;number_of_attempts:number;number_of_tutor_interactions:number;outcome:string|null}
export interface LearningSessionDetail extends LearningSessionSummary {problem:Record<string,unknown>|null;attempts:Attempt[];current_attempt_id:string|null;final_work:string;tutor_assessment:TutorAssessment|null;resource_recommendation:TutorResourceRecommendation|null}
