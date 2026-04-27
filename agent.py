from crewai import Agent, Task, Crew, Process


def get_conversation_agent():
    return Agent(
        role="English Fluency Coach",
        goal="Have a natural everyday conversation while coaching spoken English fluency.",
        backstory="""You are a warm, friendly native English speaker having a casual
        everyday chat with someone who is learning English. Think of yourself as a
        good friend — genuinely curious, easy to talk to, and naturally encouraging.

        For EVERY message, respond in exactly this format — three lines, nothing else:

        Comment: <fluency feedback>
        Suggestion: <the most natural way to say what the student said>
        Question: <follow-up question>

        Rules for Comment:
        - If the student's sentence sounds UNNATURAL: use a varied encouraging phrase
          AND include the natural version in the same sentence. For example:
          "You could say: I really like the two main characters, they have great chemistry!"
          "Try saying: I like both lead characters, they make a great team!"
          "Another way to put it: I am really into the two main characters, they work so well together!"
          Always end with one short sentence explaining why it sounds more natural.
          Rotate through different opening phrases each time:
          "You could say:", "Try saying:", "Another way to put it:",
          "It would sound more natural to say:", "A lot of people would say:",
          "You might say:"
        - If the sentence already sounds NATURAL: give a short warm reaction like
          "Oh that sounds great!", "Ha, same here!", "Nice, very natural!",
          "Love that, exactly how people say it!" — genuine and different each time.
          Never rewrite a natural sentence.

        Rules for Suggestion:
        - Always write the cleanest, most natural version of what the student said.
        - If the student's sentence is already natural, write it back exactly as they said it.
        - Write ONLY the sentence itself — no explanation, no quotes, no labels.
        - Never start with phrases like "You could say" or "Try saying" here.

        Rules for Question:
        - Ask ONE follow-up question the way a curious friend naturally would in
          real conversation — short, warm, and genuinely interested.
        - Let the conversation flow naturally. If a multiple choice question fits
          naturally in context, use it. If a simple open question fits better, use that.
        - The goal is to keep the person talking comfortably and naturally.
        - Never sound like a teacher, interviewer, or language test.

        The tone throughout should feel like texting a friend — relaxed, genuine,
        and encouraging. Your questions should make the person want to keep talking.
        Never use closing words or labels at the end of responses.""",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        verbose=False,
    )


def get_analysis_agent():
    return Agent(
        role="English Fluency Analyst",
        goal="Analyze a student's spoken English and provide a detailed fluency assessment.",
        backstory="""You are an expert English language assessor specializing in
        spoken fluency for non-native speakers. You assess speech across three
        categories: vocabulary, phrasing & expression, and sentence structure.
        You are precise, fair, and constructive in your feedback.""",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        verbose=False,
    )


def get_conversation_response(student_text: str, history: list, topic_name: str) -> tuple[str, str, str]:
    """Returns (comment, suggestion, question)."""
    agent = get_conversation_agent()
    history_str = ""
    for msg in history[-8:]:
        role = "Student" if msg["role"] == "student" else "Coach"
        history_str += f"{role}: {msg['content']}\n"

    task = Task(
        description=(
            f"Topic: {topic_name}\n"
            f"Conversation so far:\n{history_str}\n"
            f"Student just said: \"{student_text}\"\n\n"
            f"Respond using exactly this format — three lines only:\n"
            f"Comment: <feedback including the natural version of what student said>\n"
            f"Suggestion: <natural version of what student said, sentence only>\n"
            f"Question: <follow-up question>"
        ),
        expected_output=(
            "Comment: <feedback with natural version included>\n"
            "Suggestion: <natural sentence only>\n"
            "Question: <follow-up question>"
        ),
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential)
    raw = crew.kickoff().raw

    comment, suggestion, question = "", "", ""
    for line in raw.strip().splitlines():
        if line.lower().startswith("comment:"):
            comment    = line[len("comment:"):].strip()
        elif line.lower().startswith("suggestion:"):
            suggestion = line[len("suggestion:"):].strip()
        elif line.lower().startswith("question:"):
            question   = line[len("question:"):].strip()

    if not suggestion:
        suggestion = student_text

    return comment or raw.strip(), suggestion, question


def score_to_label(score: float) -> str:
    if score <= 3:  return "Beginner"
    if score <= 5:  return "Developing"
    if score <= 7:  return "Intermediate"
    if score <= 9:  return "Fluent"
    return "Mastery"


def analyze_session(turns: list) -> dict:
    agent = get_analysis_agent()
    turns_text = ""
    for i, t in enumerate(turns, 1):
        turns_text += (
            f"Turn {i}:\n"
            f"  Question: {t['app_question']}\n"
            f"  Student said: {t['student_speech']}\n"
            f"  Coach comment: {t['fluency_comment']}\n\n"
        )

    task = Task(
        description=(
            f"Analyze the following spoken English conversation turns from a student:\n\n"
            f"{turns_text}\n"
            f"Assess the student across three categories. "
            f"Respond ONLY with a JSON object in this exact format:\n"
            f"{{\n"
            f'  "vocabulary_score": <1-10>,\n'
            f'  "vocabulary_note": "<2-3 sentence assessment>",\n'
            f'  "phrasing_score": <1-10>,\n'
            f'  "phrasing_note": "<2-3 sentence assessment>",\n'
            f'  "structure_score": <1-10>,\n'
            f'  "structure_note": "<2-3 sentence assessment>",\n'
            f'  "overall_score": <1-10>,\n'
            f'  "overall_note": "<2-3 sentence overall summary>",\n'
            f'  "suggestion": "<one specific thing to focus on next session>"\n'
            f"}}"
        ),
        expected_output="A JSON object with scores and notes for each category.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential)
    raw = crew.kickoff().raw

    import json, re
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
        except Exception:
            data = {}
    else:
        data = {}

    return data or {
        "vocabulary_score": 5, "vocabulary_note": "Unable to analyze.",
        "phrasing_score": 5,   "phrasing_note": "Unable to analyze.",
        "structure_score": 5,  "structure_note": "Unable to analyze.",
        "overall_score": 5,    "overall_note": "Unable to analyze.",
        "suggestion": "Keep practicing!"
    }


def analyze_progress(sessions_data: list) -> dict:
    agent = get_analysis_agent()
    sessions_text = ""
    for i, s in enumerate(sessions_data, 1):
        sessions_text += (
            f"Session {i} (Topic: {s['topic']}):\n"
            f"  Vocabulary: {s['vocabulary_score']}/10 — {s['vocabulary_note']}\n"
            f"  Phrasing: {s['phrasing_score']}/10 — {s['phrasing_note']}\n"
            f"  Structure: {s['structure_score']}/10 — {s['structure_note']}\n"
            f"  Overall: {s['overall_score']}/10 — {s['overall_note']}\n\n"
        )

    task = Task(
        description=(
            f"Here are 5 sessions of English fluency data for a student:\n\n"
            f"{sessions_text}\n"
            f"Generate a progress report. Compare performance across the 5 sessions "
            f"and describe improvement or areas needing work. "
            f"Respond ONLY with a JSON object:\n"
            f"{{\n"
            f'  "vocabulary_score": <average 1-10>,\n'
            f'  "vocabulary_description": "<3-4 sentence progress description>",\n'
            f'  "phrasing_score": <average 1-10>,\n'
            f'  "phrasing_description": "<3-4 sentence progress description>",\n'
            f'  "structure_score": <average 1-10>,\n'
            f'  "structure_description": "<3-4 sentence progress description>",\n'
            f'  "overall_score": <average 1-10>,\n'
            f'  "improvement_description": "<3-4 sentence overall progress summary>"\n'
            f"}}"
        ),
        expected_output="A JSON object with averaged scores and progress descriptions.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential)
    raw = crew.kickoff().raw

    import json, re
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {}
