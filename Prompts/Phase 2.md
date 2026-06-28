# Phase 2 — Dictation Engine (Whisper Integration)

## Objective
Enable voice input capability inside the chatbot. Users can click the microphone button to record their voice, transcribe it using the Groq Whisper API, and automatically populate the chat input.

---

## Backend Changes

### 1. [speech.py](file:///d:/Work/PROJECTS/RAG%20based%20College%20ChatBot/speech.py)
* Create `transcribe_audio(file_bytes: bytes, filename: str) -> str` helper function.
* Use the `Groq` client instance to transcribe the audio bytes using the `whisper-large-v3` model.

### 2. [app.py](file:///d:/Work/PROJECTS/RAG%20based%20College%20ChatBot/app.py)
* Add a `/api/transcribe` POST route.
* Accept the uploaded audio file from `request.files['audio']`.
* Call the speech helper function and return `{"text": transcription_text}`.

---

## Frontend Changes

### 1. [templates/index.html](file:///d:/Work/PROJECTS/RAG%20based%20College%20ChatBot/templates/index.html)
* No structure changes needed. The microphone button `#mic-btn` is already present.

### 2. [static/style.css](file:///d:/Work/PROJECTS/RAG%20based%20College%20ChatBot/static/style.css)
* Add a `.recording` state style for `#mic-btn` to pulse red and indicate active voice recording.

### 3. [static/script.js](file:///d:/Work/PROJECTS/RAG%20based%20College%20ChatBot/static/script.js)
* Re-implement the `#mic-btn` click handler.
* Use `navigator.mediaDevices.getUserMedia({ audio: true })` to capture audio.
* Initialize `MediaRecorder` to gather audio chunks.
* Toggle recording states (visual pulse and mic icon changes).
* On stop, convert chunks to a `Blob`, build a `FormData` object, upload it to `/api/transcribe`, and place the returned transcription into the `#chat-input` textarea.
