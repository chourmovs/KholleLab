export interface ProblemSource { type: string; name: string; year?: number; session?: string; url?: string }
export interface ProblemSummary { id:string; title:string; subtitle?:string; level:string; difficulty:number; estimatedMinutes?:number; year?:number; topics:string[]; source:ProblemSource }
export interface ProblemDetail extends ProblemSummary { statement:string; hintLevels:number[] }
