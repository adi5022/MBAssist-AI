from typing import Optional
from pydantic import BaseModel, Field
from langdetect import detect
from langgraph.graph import StateGraph, END

from config import LANGUAGE_NAMES, TOP_K
from llm import get_llm, PLANNER_SYS, ANSWER_SYS, FALLBACK_SYS, CRITIQUE_SYS
from knowledge import get_vector_store

# ─── State schema ─────────────────────────────────────────────
class ChatState(BaseModel):
    query:       str            = Field(...)
    lang_code:   str            = "en"
    lang_name:   str            = "English"
    action:      Optional[str]  = None
    docs:        Optional[list] = None
    answer:      Optional[str]  = None

def detect_language(text: str) -> tuple[str, str]:
    """Returns (lang_code, lang_name)."""
    try:
        code = detect(text)
    except Exception:
        code = "en"
    name = LANGUAGE_NAMES.get(code, code.upper())
    return code, name

def node_detect_language(state: ChatState) -> ChatState:
    code, name          = detect_language(state.query)
    state.lang_code     = code
    state.lang_name     = name
    print(f"  [lang]      {name} ({code})")
    return state

def node_planner(state: ChatState) -> ChatState:
    routing_prompt = (
        f"User question (may be in {state.lang_name}): {state.query}\n\n"
        "Route this: reply ONLY with 'retrieve' or 'answer_direct'."
    )
    llm = get_llm()
    decision = llm.chat(PLANNER_SYS, routing_prompt, max_tokens=8)
    state.action = "retrieve" if "retrieve" in decision.lower() else "answer_direct"
    print(f"  [planner]   {state.action}")
    return state

def node_retrieve(state: ChatState) -> ChatState:
    vector_store = get_vector_store()
    results = vector_store.search(state.query, k=TOP_K)
    state.docs = results
    if results:
        print(f"  [retriever] top score={results[0]['score']:.3f}  page={results[0]['page']}")
    return state

def node_answer(state: ChatState) -> ChatState:
    sys_prompt = ANSWER_SYS.format(
        lang_name=state.lang_name, lang_code=state.lang_code
    ) if state.docs else FALLBACK_SYS.format(
        lang_name=state.lang_name, lang_code=state.lang_code
    )

    llm = get_llm()
    if state.docs:
        passages = "\n\n".join(
            f"[Page {d['page']} | relevance {d['score']:.2f}]\n{d['text']}"
            for d in state.docs
        )
        user_msg = (
            f"Context from MBCET Admissions Prospectus:\n{passages}\n\n"
            f"Question ({state.lang_name}): {state.query}"
        )
    else:
        user_msg = state.query

    state.answer = llm.chat(sys_prompt, user_msg, max_tokens=700)
    return state

def node_verifier(state: ChatState) -> ChatState:
    # Compile extracted context excerpts to check grounding
    passages = ""
    if state.docs:
        passages = "\n\n".join(
            f"[Page {d['page']}]\n{d['text']}" for d in state.docs
        )
    else:
        passages = "No prospectus context was retrieved (direct answer)."
    
    critique_prompt = (
        f"Prospectus Context:\n{passages}\n\n"
        f"User Query: {state.query}\n\n"
        f"Draft Answer:\n{state.answer}"
    )
    
    llm = get_llm()
    verified_answer = llm.chat(CRITIQUE_SYS, critique_prompt, max_tokens=700)
    state.answer = verified_answer
    print("  [verifier]  Audited and finalized response.")
    return state

# ─── StateGraph Build ──────────────────────────────────────────
graph = StateGraph(ChatState)

graph.add_node("detect_language", node_detect_language)
graph.add_node("planner",         node_planner)
graph.add_node("retriever",       node_retrieve)
graph.add_node("answer",          node_answer)
graph.add_node("verifier",        node_verifier)

graph.set_entry_point("detect_language")
graph.add_edge("detect_language", "planner")

graph.add_conditional_edges(
    "planner",
    lambda s: s.action,
    {"retrieve": "retriever", "answer_direct": "answer"},
)
graph.add_edge("retriever", "answer")
graph.add_edge("answer",    "verifier")
graph.add_edge("verifier",  END)

graph_app = graph.compile()
print("[OK] LangGraph workflow compiled for MBCET Chatbot")

def ask_chatbot(question: str) -> dict:
    """Run the RAG pipeline for the given question and return state dictionary."""
    result = graph_app.invoke({"query": question})
    return result
