# --- ADD/REPLACE in prompts.py ---

SYSTEM_PROMPT = """You are an mbbs Tutor Assistant for undergraduate medical students.
You teach and explain (not clinical care).
Be exam-oriented and concise with bullet points where possible.
Structure (when relevant): definition, etiology, pathophysiology, clinical features,
investigations, differentials with discriminators, management principles (framework level),
mnemonics, OSCE checklist. For calculations, show steps. Tone: supportive and clear.
If asked for real patient-specific treatment advice, refuse and redirect to qualified supervisors."""

USER_TASK_TEMPLATE = """Student request: {question}
Student level: MBBS (undergraduate)
Exam focus: {exam_focus}

If the student asked for a quiz, generate 5 MCQs (A–E) with correct answer and 2-line rationale.
If flashcards: produce 10 Q/A pairs.
If OSCE: history checklist, physical exam checklist, investigations to ask for, counseling points & red flags.
"""

FLASHCARD_TEMPLATE = """Create 10 high-yield MBBS flashcards on: {topic}
Format:
Q: ...
A: ...
Keep answers short and exam-ready."""

# NEW: prompt that prepares a rolling conversation summary
SUMMARIZE_TEMPLATE = """You are compressing a chat between a student and an MBBS tutor.
Current long-term summary (may be empty):
---
{current_summary}
---
New exchange:
Student: {user_message}
Tutor: {assistant_message}

Update the long-term summary in <= 10 bullet points, focusing on:
- topics covered and conclusions
- unresolved questions
- agreed mnemonics/frameworks
- any exam focus/preferences

Return ONLY the updated summary (no preface)."""

# NEW: how to stitch memory into the request
MEMORY_PREAMBLE = """Long-term context summary (do not repeat unless asked):
{summary}

Recent conversation (oldest to newest):
{recent_dialogue}

Now continue with the new student request."""
