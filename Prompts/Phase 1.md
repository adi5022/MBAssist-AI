# Phase 1 — Modularize Version 1

The V2 Development Specification is the architectural source of truth.

The existing Version 1 Python project is the implementation reference.

Your task is **only** Phase 1.

---

# Objective

Transform the existing notebook into a modular Python web application while preserving every existing feature.

The application should behave exactly like Version 1.

Do not improve the AI yet.

Do not redesign the retrieval system.

Do not replace embeddings.

Do not add speech-to-text.

Do not implement website scraping.

Do not optimize routing.

Simply reorganize the project into a maintainable architecture.

---

# Primary Goal

Move the existing implementation into the following structure:

```text
project/

app.py
config.py
knowledge.py
rag.py
llm.py
scraper.py
speech.py

templates/
    index.html

static/
    style.css
    script.js

data/
cache/
```

Only create additional modules if there is a compelling architectural reason.

---

# Responsibilities

## app.py

* Web server
* API endpoints
* Connect frontend with backend

---

## knowledge.py

Move all existing knowledge-related logic here:

* PDF loading
* Chunking
* Embeddings
* FAISS
* Retrieval

Do not change how it works.

---

## rag.py

Move:

* LangGraph
* State
* Routing
* Workflow

Preserve behavior exactly.

---

## llm.py

Move:

* Groq client
* Prompt templates
* LLM helper functions

---

## scraper.py

Create as an empty placeholder for future work.

---

## speech.py

Create as an empty placeholder for future work.

---

# Frontend

Create a minimal HTML interface.

Requirements:

* Chat history
* Input field
* Send button

Nothing else.

No styling beyond basic readability.

---

# Refactoring Rules

Do not rewrite working code.

Move code instead of replacing it.

Preserve behavior.

Improve readability.

Keep the project beginner-friendly.

---

# Workflow

Before generating code:

1. Explain your modularization plan.
2. Explain why each subsystem exists.
3. Explain what code belongs in each file.

Then implement the refactor.

---

# Success Criteria

Phase 1 is complete only when:

* The notebook has been converted into a modular Python project.
* The chatbot works exactly as Version 1.
* The chatbot runs through a Python backend.
* Messages can be sent and received through the HTML interface.

After completing Phase 1, stop and wait for the next task. Do not begin implementing later phases.
