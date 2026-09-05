import {act,render,screen,waitFor} from "@testing-library/react";
import {beforeEach,expect,it,vi} from "vitest";
import {ProfessorPanel} from "../professor-panel";
import * as api from "@/lib/api";
import {useAttemptStore} from "@/stores/useAttemptStore";

vi.mock("@/lib/api",async importOriginal=>({...await importOriginal<typeof import("@/lib/api")>(),getEvaluation:vi.fn(),createEvaluation:vi.fn(),retryEvaluation:vi.fn()}));
const running=(stage:"queued"|"candidate_audit"|"adjudication"|"finalizing",progress:number)=>({status:"running" as const,stage,progress,max_score:20,strengths:[],issues:[],missing_justifications:[]});
const completed={...running("finalizing",95),status:"completed" as const,stage:"completed" as const,progress:100,score:18,verdict:"correct",provider:"huggingface",model:"Qwen/Qwen3-32B:nscale",inference_backend:"nscale"};
beforeEach(()=>{vi.clearAllMocks();useAttemptStore.setState({attemptId:"attempt-1",status:"submitted"})});
it("restores an adjudication already running after reload",async()=>{vi.mocked(api.getEvaluation).mockResolvedValue(running("adjudication",60));render(<ProfessorPanel/>);expect(await screen.findByText("● Comparaison au corrigé")).toBeInTheDocument();expect(screen.getByText("✓ Analyse du raisonnement")).toBeInTheDocument()});
it("queues rapidly then polls through completion",async()=>{vi.useFakeTimers({shouldAdvanceTime:true});vi.mocked(api.getEvaluation).mockRejectedValueOnce(new api.ApiError(404)).mockResolvedValueOnce(running("candidate_audit",25)).mockResolvedValueOnce(completed);vi.mocked(api.createEvaluation).mockResolvedValue(running("queued",5));render(<ProfessorPanel/>);await waitFor(()=>expect(screen.getByRole("button",{name:"Examiner ma copie"})).toBeInTheDocument());await act(async()=>screen.getByRole("button",{name:"Examiner ma copie"}).click());expect(screen.getByText("○ Analyse du raisonnement")).toBeInTheDocument();await act(async()=>vi.advanceTimersByTimeAsync(2100));expect(screen.getByText("● Analyse du raisonnement")).toBeInTheDocument();await act(async()=>vi.advanceTimersByTimeAsync(2100));expect(screen.getByText(/DÉBRIEF DE COLLE/)).toBeInTheDocument();vi.useRealTimers()});
