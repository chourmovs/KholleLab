import {act,cleanup,fireEvent,render,screen} from "@testing-library/react";
import {afterEach,beforeEach,describe,expect,it,vi} from "vitest";
import {SpeechDictationControl} from "./speech-dictation-control";
import type {BrowserSpeechRecognition,SpeechRecognitionResultLike} from "@/lib/speech-recognition";

class MockRecognition implements BrowserSpeechRecognition {
 static instances:MockRecognition[]=[];lang="";interimResults=false;continuous=true;onstart:(()=>void)|null=null;onresult:BrowserSpeechRecognition["onresult"]=null;onerror:BrowserSpeechRecognition["onerror"]=null;onend:(()=>void)|null=null;start=vi.fn(()=>this.onstart?.());stop=vi.fn(()=>this.onend?.());abort=vi.fn();
 constructor(){MockRecognition.instances.push(this)}
 result(...chunks:Array<{text:string;final:boolean}>){const results=chunks.map(({text,final})=>Object.assign([{transcript:text}],{isFinal:final,length:1})) as SpeechRecognitionResultLike[];this.onresult?.({resultIndex:0,results})}
}
const renderControl=(properties:Partial<React.ComponentProps<typeof SpeechDictationControl>>={})=>render(<SpeechDictationControl onFinal={vi.fn()} {...properties}/>);
beforeEach(()=>{MockRecognition.instances=[];Object.assign(window,{SpeechRecognition:MockRecognition,webkitSpeechRecognition:undefined})});
afterEach(()=>{cleanup();Reflect.deleteProperty(window,"SpeechRecognition");Reflect.deleteProperty(window,"webkitSpeechRecognition")});

describe("speech dictation",()=>{
 it("keeps unsupported workspaces usable and never starts",()=>{Reflect.deleteProperty(window,"SpeechRecognition");renderControl();expect(screen.getByText("Dictée vocale indisponible sur ce navigateur.")).toBeInTheDocument();expect(MockRecognition.instances).toHaveLength(0)});
 it("starts only after an explicit click and shows listening state",()=>{renderControl();expect(MockRecognition.instances).toHaveLength(0);fireEvent.click(screen.getByRole("button",{name:"Dicter mon raisonnement"}));expect(MockRecognition.instances[0].start).toHaveBeenCalledOnce();expect(screen.getByRole("button",{name:"Arrêter la dictée"})).toHaveTextContent("Écoute…")});
 it("shows interim text without inserting it, then inserts each final chunk exactly once",()=>{const onFinal=vi.fn();renderControl({onFinal});fireEvent.click(screen.getByRole("button"));const recognition=MockRecognition.instances[0];act(()=>recognition.result({text:"je développe",final:false}));expect(screen.getByText("je développe")).toBeInTheDocument();expect(onFinal).not.toHaveBeenCalled();act(()=>recognition.result({text:"donc x vaut deux",final:true},{text:"la fonction croît",final:true}));expect(onFinal.mock.calls).toEqual([["donc x vaut deux"],["la fonction croît"]])});
 it("stops cleanly on a second tap",()=>{renderControl();fireEvent.click(screen.getByRole("button"));const recognition=MockRecognition.instances[0];fireEvent.click(screen.getByRole("button",{name:"Arrêter la dictée"}));expect(recognition.stop).toHaveBeenCalledOnce()});
 it("reports permission failure inline without inserting",()=>{const onFinal=vi.fn();renderControl({onFinal});fireEvent.click(screen.getByRole("button"));act(()=>MockRecognition.instances[0].onerror?.({error:"not-allowed"}));expect(screen.getByText(/Accès au microphone refusé/)).toBeInTheDocument();expect(onFinal).not.toHaveBeenCalled()});
 it("discards stale results after a problem change and aborts on unmount",()=>{const onFinal=vi.fn();const view=render(<SpeechDictationControl onFinal={onFinal} contextKey="one"/>);fireEvent.click(screen.getByRole("button"));const first=MockRecognition.instances[0];view.rerender(<SpeechDictationControl onFinal={onFinal} contextKey="two"/>);expect(first.abort).toHaveBeenCalledOnce();act(()=>first.result({text:"ancien exercice",final:true}));expect(onFinal).not.toHaveBeenCalled();fireEvent.click(screen.getByRole("button"));const second=MockRecognition.instances[1];view.unmount();expect(second.abort).toHaveBeenCalledOnce()});
 it("is unavailable on a submitted board",()=>{renderControl({disabled:true});expect(screen.getByRole("button",{name:"Dicter mon raisonnement"})).toBeDisabled();fireEvent.click(screen.getByRole("button"));expect(MockRecognition.instances).toHaveLength(0)});
});
