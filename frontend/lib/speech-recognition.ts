export interface SpeechRecognitionAlternativeLike {transcript:string}
export interface SpeechRecognitionResultLike {isFinal:boolean;length:number;[index:number]:SpeechRecognitionAlternativeLike}
export interface SpeechRecognitionEventLike {resultIndex:number;results:ArrayLike<SpeechRecognitionResultLike>}
export interface SpeechRecognitionErrorEventLike {error:string}
export interface BrowserSpeechRecognition {lang:string;interimResults:boolean;continuous:boolean;onstart:(()=>void)|null;onresult:((event:SpeechRecognitionEventLike)=>void)|null;onerror:((event:SpeechRecognitionErrorEventLike)=>void)|null;onend:(()=>void)|null;start():void;stop():void;abort():void}
type SpeechRecognitionConstructor=new()=>BrowserSpeechRecognition;
type SpeechWindow=Window&{SpeechRecognition?:SpeechRecognitionConstructor;webkitSpeechRecognition?:SpeechRecognitionConstructor};
function constructor():SpeechRecognitionConstructor|undefined {if(typeof window==="undefined")return undefined;const speechWindow=window as SpeechWindow;return speechWindow.SpeechRecognition??speechWindow.webkitSpeechRecognition}
export function speechRecognitionSupported():boolean{return Boolean(constructor())}
export function createSpeechRecognition():BrowserSpeechRecognition|null {const Recognition=constructor();if(!Recognition)return null;const recognition=new Recognition();recognition.lang="fr-FR";recognition.interimResults=true;recognition.continuous=false;return recognition}
export function normalizeDictation(text:string):string {return text.replace(/\s+/g," ").trim()}
