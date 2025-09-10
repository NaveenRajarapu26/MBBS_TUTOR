# --- REPLACE your app.py with this (keeps your routes but adds memory) ---

import os
from flask import Flask, render_template, request, jsonify, make_response
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

from models import (
    init_db, get_or_create_conversation, save_message,
    get_recent_messages, update_summary
)
from prompts import (
    SYSTEM_PROMPT, USER_TASK_TEMPLATE, FLASHCARD_TEMPLATE,
    MEMORY_PREAMBLE, SUMMARIZE_TEMPLATE
)

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY in environment or .env")

MODEL_NAME = os.getenv("GROQ_MODEL", "Gemma2-9b-It")  # or llama-3.1-70b-versatile

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

init_db()

llm = ChatGroq(model=MODEL_NAME, groq_api_key=GROQ_API_KEY)
parser = StrOutputParser()

# Base task prompts
explain_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{memory}\n\n" + USER_TASK_TEMPLATE),
])
flash_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{memory}\n\n" + FLASHCARD_TEMPLATE),
])
# Summarizer
summarize_prompt = ChatPromptTemplate.from_template(SUMMARIZE_TEMPLATE)

RECENT_LIMIT = int(os.getenv("RECENT_LIMIT", "12"))    # number of recent turns to include
SUMMARY_EVERY = int(os.getenv("SUMMARY_EVERY", "6"))   # update summary after this many user turns

def format_dialogue(messages):
    # messages: list[Message] (oldest→newest)
    lines = []
    for m in messages:
        role = "Student" if m.role == "user" else "Tutor"
        lines.append(f"{role}: {m.content}")
    return "\n".join(lines)

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/ask")
def ask():
    """
    JSON/form:
      question: str
      mode: 'explain' | 'quiz' | 'flashcards' | 'osce'
      exam_focus: optional, default "Final MBBS"
    """
    data = request.get_json() if request.is_json else request.form
    question = (data.get("question") or "").strip()
    mode = (data.get("mode") or "explain").strip().lower()
    exam_focus = (data.get("exam_focus") or "Final MBBS").strip()
    if not question:
        return jsonify({"ok": False, "error": "question is required"}), 400

    # Ensure we have a session id
    sid = request.cookies.get("sid")
    conv = get_or_create_conversation(sid)

    # Pull memory
    recent_msgs = get_recent_messages(conv.id, limit=RECENT_LIMIT)
    recent_dialogue = format_dialogue(recent_msgs)
    memory_text = MEMORY_PREAMBLE.format(
        summary=conv.summary or "(none yet)",
        recent_dialogue=recent_dialogue or "(no recent messages)"
    )

    # Build prompt with memory injected
    if mode == "flashcards":
        filled = flash_prompt.format_messages(memory=memory_text, topic=question)
    else:
        q_full = f"[MODE: {mode.upper()}]\n{question}"
        filled = explain_prompt.format_messages(memory=memory_text, question=q_full, exam_focus=exam_focus)

    # Store user message then call LLM
    save_message(conv.id, "user", question)
    text = (llm | parser).invoke(filled)
    save_message(conv.id, "assistant", text)

    # Periodically update long-term summary
    if ((len(recent_msgs) + 1) // 2 + 1) % SUMMARY_EVERY == 0:  # rough "user-turns" count
        # Use last user+assistant to update summary
        last_user = question
        last_assistant = text
        summary_filled = summarize_prompt.format_messages(
            current_summary=conv.summary or "",
            user_message=last_user,
            assistant_message=last_assistant
        )
        new_summary = (llm | parser).invoke(summary_filled).strip()
        # Basic guard: avoid exploding summary
        if len(new_summary) > 4000:
            new_summary = new_summary[:4000] + " ..."
        update_summary(conv.id, new_summary)

    # Return with a cookie if needed
    resp = make_response(jsonify({"ok": True, "mode": mode, "answer": text}))
    if not sid:
        resp.set_cookie("sid", conv.sid, httponly=True, samesite="Lax", secure=False)
    return resp

@app.get("/history")
def history():
    sid = request.cookies.get("sid")
    conv = get_or_create_conversation(sid)
    msgs = get_recent_messages(conv.id, limit=100)
    out = [{"role": m.role, "content": m.content, "at": m.created_at.isoformat()} for m in msgs]
    return jsonify({"ok": True, "sid": conv.sid, "summary": conv.summary, "messages": out})

@app.get("/health")
def health():
    return {"ok": True, "service": "MBBS Tutor Assistant with Memory"}

if __name__ == "__main__":
    # Local dev
    app.run(host="0.0.0.0", port=5000, debug=True)