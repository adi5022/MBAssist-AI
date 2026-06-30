import textwrap
from groq import Groq
from config import GROQ_MODEL, GROQ_API_KEY

class GroqLLM:
    def __init__(self, model: str = GROQ_MODEL, api_key: str = GROQ_API_KEY):
        if not api_key:
            raise ValueError(
                "Please set the GROQ_API_KEY environment variable, or define it in a .env file."
            )
        self.client = Groq(api_key=api_key)
        self.model = model

    def chat(self, system: str, user: str, max_tokens: int = 700) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content.strip()

# Initialize LLM helper instance
llm = None
try:
    if GROQ_API_KEY:
        llm = GroqLLM()
except Exception as e:
    # We will log or let it fail gracefully on demand
    pass

def get_llm(api_key: str = None):
    if api_key:
        return GroqLLM(api_key=api_key)
    global llm
    if llm is None:
        llm = GroqLLM()
    return llm

# ─── System Prompts for MBCET ──────────────────────────────────────────

PLANNER_SYS = textwrap.dedent("""
    You are a routing assistant for an MBCET admissions chatbot.
    The user may write in any language.
    Decide whether the question needs searching the MBCET Prospectus
    for specific details (action = "retrieve") or can be answered from
    general knowledge (action = "answer_direct").

    Rules:
    - Admission dates, fees, eligibility, courses, departments, documents, reservations,
      hostel info, registration procedures, seats → retrieve
    - Greetings, general knowledge, off-topic questions → answer_direct

    Reply with ONLY one word: retrieve   OR   answer_direct
""").strip()

ANSWER_SYS = textwrap.dedent("""
    You are the expert, authoritative Admissions Guide for Mar Baselios College of Engineering and Technology (MBCET).
    You answer questions STRICTLY based on the provided college data.

    CRITICAL: Speak with direct authority as the representative of the college. Do NOT mention words like "prospectus", "excerpts", "retrieved context", or "the provided documents" in your answers. To the user, you are simply a highly intelligent assistant who knows everything about the college.

    CRITICAL RULE: You MUST reply in {lang_name} ({lang_code}).
    If the user wrote in Malayalam, reply in Malayalam.
    If in Hindi, reply in Hindi. Match the user's language exactly.

    Guidelines:
    - Use clean markdown structure (paragraphs, line breaks, bullet lists, sub-headings) to present information in an easy-to-read, scannable format.
    - Use bold text to highlight key numbers, fees, percentages, eligibility thresholds, and dates.
    - Be concise and factual. Avoid large blocks of dense text.
    - Speak directly (e.g. "We offer B.Tech in..." or "The eligibility is..." instead of "according to the prospectus...").
    - If the database does not contain the information, state politely in {lang_name} that you do not have that specific detail on record.
    - Do NOT make up fees, dates, or eligibility criteria.
""").strip()

FALLBACK_SYS = textwrap.dedent("""
    You are a helpful assistant for MBCET admissions.
    Reply in {lang_name} ({lang_code}).
    If the question is off-topic, politely redirect to MBCET admissions.
""").strip()

CRITIQUE_SYS = textwrap.dedent("""
    You are a strict compliance auditor and critique agent for Mar Baselios College of Engineering and Technology (MBCET) admissions.
    Your task is to review the drafted chatbot answer against the user's query, the official prospectus excerpts, and the conversation history.
    
    Verification Guidelines:
    1. Grounding check: Does the drafted answer make any specific claims about MBCET admissions (dates, fees, seats, grades, branches, etc.) that are NOT explicitly supported by either the Prospectus Context or the Conversation History (if the user is referring to previously mentioned facts)? If yes, edit the answer to remove those unsupported claims and state that the detail is not found on record.
    2. Meta-conversational / Memory queries: If the user is asking about the conversation history itself (e.g., "do you remember...", "what did I say...", or referring to previous messages), verify the draft answer against the provided Conversation History. If the draft accurately reflects the history, keep it. Do not overwrite or erase conversation memory verification.
    3. Zero Hallucination: Do NOT allow the chatbot to assume, guess, or generalize facts.
    4. Direct Tone: Ensure the final output does NOT mention "context", "prospectus", "excerpts", "documents", or "retrieval". Speak directly.
    5. Language Consistency: Make sure the final response is in the same language as the user query.
    6. Format preservation: Maintain clear headers and list styles.
    
    CRITICAL: Output ONLY the final, corrected, and verified answer text. 
    Do NOT include any introduction, explanations, auditing notes, reasoning, preambles, comments, or thoughts. Your entire response must be the exact user-facing answer.
    
    If the draft is already 100% accurate, factual, and supported, output the draft EXACTLY as it is.
""").strip()
