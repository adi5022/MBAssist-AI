# MBAssist AI — Admissions Chatbot for MBCET

MBAssist AI is an advanced, multilingual, retrieval-augmented generation (RAG) admissions chatbot built specifically for **Mar Baselios College of Engineering and Technology (MBCET)**. The bot guides prospective students through admissions rules, fee structures, courses, and eligibility details, supporting both voice and text inputs.

---

## 🌟 Standout Features

### 1. Hybrid Memory Architecture (Sliding Window + Abstract Summarization)
To prevent prompt context window bloat and manage API tokens efficiently:
* **Recent Zone**: The chatbot retains the last `4` messages (2 turns) in full detail to preserve immediate references.
* **Archive Zone**: Older messages are dynamically compiled into a single, cohesive paragraph summary using a background LLM summarization call and saved to the SQL database.
* **Result**: The bot maintains long-term conversational memory with strict token bounds.

### 2. Multi-tenant Custom API Keys (Zero Hosting Billing Cost)
* Users can optionally input their **own Groq API Key** on registration/login.
* The backend securely stores this key and instantiates the LLM client on the fly for their queries, keeping the host's hosting bill completely free!

### 3. Secure SQLite Backend & Session Management
* **SQLite Database**: Native, zero-setup relational database storing users, chat sessions (timelines), and message logs.
* **PBKDF2 Password Hashing**: Utilizes high-security hashing with unique random salts for user password storage.
* **Session Timelines**: Users can create, save, and recall distinct conversations.

### 4. Multilingual Speech-to-Text & Radial Selector Wheel
* Supports voice dictation in English and Malayalam.
* Uses a **Radial Choice Wheel** (fanning EN, MIX, ML buttons in an arc) for language selection.
* Dynamically routes STT calls to **Sarvam AI** for Malayalam transcripts and falls back to **Groq Whisper** if credentials are dry or if English is selected.

---

## 🛠️ Tech Stack
* **Backend**: Python, Flask, SQLite
* **RAG Orchestrator**: LangGraph (StateGraph), FAISS Vector Index (LSA Semantic Search)
* **LLM Engine**: Groq (Llama-3.3-70b-versatile)
* **STT Providers**: Sarvam AI API, Groq Whisper
* **Frontend**: HTML5, Vanilla CSS, JS
