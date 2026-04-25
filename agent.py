from crewai import Agent, Task, Crew, Process

def get_conversation_agent():
    return Agent(
        role="English Fluency Coach",
        goal="Have a natural everyday conversation while coaching spoken English fluency.",
        backstory="""You are a warm, friendly native English speaker having a casual
        everyday chat with someone who is learning English. Think of yourself as a
        good friend — genuinely curious, easy to talk to, and naturally encouraging.

        For EVERY message, respond in exactly this format — two lines, nothing else:

        Comment: <fluency feedback>
        Question: <follow-up question>

        Rules for Comment:
        - If the student's sentence sounds UNNATURAL: suggest a more natural version
          using varied, encouraging phrases. Rotate through different openings such as:
          "You could say...", "Try saying...", "Another way to put it is...",
          "It would sound more natural to say...", "A lot of people would say...",
          "You might also hear people say...". Then in one sentence explain why
          it sounds more natural. Focus on word choice or phrasing, not grammar rules.
        - If the sentence already sounds NATURAL: give a short warm reaction that
          varies each time — like "Oh that sounds great!", "Ha, same here!",
          "Nice, that's exactly how people say it!", "Love that, very natural!"
          — genuine and different each time, not scripted.

        Rules for Question:
        - Ask ONE follow-up question the way a curious friend naturally would in
          real conversation — short, warm, and genuinely interested.
        - Let the conversation flow naturally. If a multiple choice question fits
          naturally in context, use it. If a simple open question fits better, use that.
        - The goal is to keep the person talking comfortably and naturally.
        - Never sound like a teacher, interviewer, or language test.

        The tone throughout should feel like texting a friend — relaxed, genuine,
        and encouraging. Your questions should make the person want to keep talking.
        Never use closing words like 'Closing:' or any label at the end of responses.""",
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

def get_conversation_response(student_text: str, history: list, topic_name: str) -> tuple[str, str]:
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
            f"Respond using exactly:\nComment: <feedback>\nQuestion: <follow-up question>"
        ),
        expected_output="Comment: <feedback>\nQuestion: <follow-up question>",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential)
    raw = crew.kickoff().raw
    comment, question = "", ""
    for line in raw.strip().splitlines():
        if line.lower().startswith("comment:"):
            comment = line[len("comment:"):].strip()
        elif line.lower().startswith("question:"):
            question = line[len("question:"):].strip()
    return comment or raw.strip(), question


def score_to_label(score: float) -> str:
    if score <= 3:   return "Beginner"
    if score <= 5:   return "Developing"
    if score <= 7:   return "Intermediate"
    if score <= 9:   return "Fluent"
    return "Mastery"


def extract_suggestion(comment: str, student_speech: str) -> str:
    """
    Extract the suggested natural version from a comment.
    If no suggestion found, return the student's original speech.
    """
    import re
    patterns = [
        r'[Yy]ou could say[,:]?\s*["\']?(.+?)["\']?(?:\s*because|\s*as|\.|$)',
        r'[Tt]ry saying[,:]?\s*["\']?(.+?)["\']?(?:\s*because|\s*as|\.|$)',
        r'[Aa]nother way to put it is[,:]?\s*["\']?(.+?)["\']?(?:\s*because|\s*as|\.|$)',
        r'[Ii]t would sound more natural to say[,:]?\s*["\']?(.+?)["\']?(?:\s*because|\s*as|\.|$)',
        r'[Aa] lot of people would say[,:]?\s*["\']?(.+?)["\']?(?:\s*because|\s*as|\.|$)',
        r'[Yy]ou might also hear people say[,:]?\s*["\']?(.+?)["\']?(?:\s*because|\s*as|\.|$)',
        r'[Aa] more natural way to say this is[,:]?\s*["\']?(.+?)["\']?(?:\s*because|\s*as|\.|$)',
    ]
    for pattern in patterns:
        match = re.search(pattern, comment)
        if match:
            return match.group(1).strip().strip('"\'')
    return student_speech


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
        data = json.loads(match.group())
    else:
        data = {
            "vocabulary_score": 5, "vocabulary_note": "Unable to analyze.",
            "phrasing_score": 5,   "phrasing_note": "Unable to analyze.",
            "structure_score": 5,  "structure_note": "Unable to analyze.",
            "overall_score": 5,    "overall_note": "Unable to analyze.",
            "suggestion": "Keep practicing!"
        }
    return data


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
        return json.loads(match.group())
    return {}
