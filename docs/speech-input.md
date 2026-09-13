# Speech input (PR61)

Speech dictation is a progressive-enhancement input method for the unified MathLive blackboard. It is not an oral attempt and it does not change scoring, mastery, XP, tutoring, or examination semantics.

## Browser and privacy boundary

KHOLLELAB uses the browser's `SpeechRecognition` implementation (or Chromium's `webkitSpeechRecognition`) in French (`fr-FR`). Availability and speech processing therefore depend on the browser and platform. Unsupported browsers keep the complete blackboard and both native and scientific keyboard input; the interface simply explains that dictation is unavailable.

Recognition starts only after the learner activates **Dicter**. KHOLLELAB does not record audio files, persist microphone audio, send microphone audio to the KHOLLELAB backend, or log transcripts. Depending on its implementation, the browser/platform may use a remote recognition service under its own privacy terms.

Interim text is ephemeral status feedback. Only final recognition results are inserted at the current MathLive caret and then become ordinary learner work through the existing solution/autosave path. No separate transcript, editor, attempt, or speech save endpoint exists.

Active recognition is cancelled when the problem or read-only state changes and when the control unmounts. Permission denial, missing audio capture, no speech, aborts, and unavailable recognition are inline non-destructive states. TTS is not implemented in PR61.

## Device acceptance

Automated tests use a deterministic recognition mock and require no microphone or network. Before release, explicitly validate microphone permission, caret insertion, continued Android/scientific keyboard input, reload, and submission in both Chrome Android and the installed KHOLLELAB TWA; browser automation cannot establish OS microphone behavior.
