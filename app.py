import os
import io
import base64
import random
import tempfile
import time
from dotenv import load_dotenv
from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from flask_bcrypt import Bcrypt
from groq import Groq
from gtts import gTTS

from models import db, User, Session as DBSession, Turn, SessionAnalysis, ProgressReport
from agent import (get_conversation_response, analyze_session,
                   analyze_progress, score_to_label)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

# Fix Render's postgres:// -> postgresql:// for SQLAlchemy 2.0
db_url = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

TOPICS = [
    {"name": "At a coffee shop",          "opening": "I just tried that new cafe on the corner. Have you been there yet?"},
    {"name": "Weekend plans",             "opening": "So what are you up to this weekend? Got anything fun planned?"},
    {"name": "Talking about the weather", "opening": "Can you believe how hot it has been lately? Is it like this where you live?"},
    {"name": "Recommending a restaurant", "opening": "I had the most amazing dinner last night. Do you have a favourite restaurant around here?"},
    {"name": "Talking about a movie",     "opening": "I watched a really good movie last night. Have you seen anything good recently?"},
    {"name": "Monday morning small talk", "opening": "Hey, how was your weekend? Do anything interesting?"},
    {"name": "Talking about a hobby",     "opening": "I have been trying to get into running lately. Do you have any hobbies you are really into?"},
    {"name": "Planning a trip",           "opening": "I am thinking about taking a trip somewhere next month. Have you travelled anywhere nice lately?"},
    {"name": "Talking about food",        "opening": "I have been trying to cook more at home. Do you enjoy cooking?"},
    {"name": "Catching up with a friend", "opening": "It feels like we have not talked in ages! What have you been up to lately?"},
    {"name": "Talking about work",        "opening": "Work has been so busy for me lately. How about you, are things busy at your end?"},
    {"name": "Talking about a TV show",   "opening": "I just finished watching a really good series. Are you watching anything good right now?"},
    {"name": "Shopping",                  "opening": "I went to the mall yesterday and it was packed! Do you enjoy shopping?"},
    {"name": "Health and exercise",       "opening": "I have been trying to go to the gym more regularly. Do you exercise much?"},
    {"name": "Talking about pets",        "opening": "My neighbour just got a puppy and it is so cute! Do you have any pets?"},
]

MAX_TURNS = 5

# Create tables on startup
with app.app_context():
    db.create_all()

# ── Auth helpers ──────────────────────────────────────────────────────────────
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── Audio helpers ─────────────────────────────────────────────────────────────
def make_audio_b64(text: str) -> str:
    if not text:
        return ""
    text = text[:500] if len(text) > 500 else text
    for attempt in range(3):
        try:
            tts = gTTS(text=text, lang="en", slow=False)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            return base64.b64encode(buf.read()).decode()
        except Exception:
            if attempt < 2:
                time.sleep(2)
    return ""

def transcribe(audio_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        f.flush()
        with open(f.name, "rb") as af:
            result = groq_client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=af,
                language="en",
            )
    return result.text.strip()

# ── Routes: Auth ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form["name"].strip()
        email    = request.form["email"].strip().lower()
        password = request.form["password"]
        role     = request.form.get("role", "student")

        if User.query.filter_by(email=email).first():
            return render_template("register.html", error="Email already registered.")

        hashed = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(name=name, email=email, password_hash=hashed, role=role)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form["email"].strip().lower()
        password = request.form["password"]
        user     = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid email or password.")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ── Routes: Dashboard ─────────────────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "teacher":
        students = User.query.filter_by(role="student").all()
        return render_template("teacher_dashboard.html", students=students)
    else:
        sessions = (DBSession.query
                    .filter_by(user_id=current_user.id)
                    .order_by(DBSession.date.desc())
                    .all())
        latest_report = (ProgressReport.query
                         .filter_by(user_id=current_user.id)
                         .order_by(ProgressReport.report_number.desc())
                         .first())
        return render_template("student_dashboard.html",
                               sessions=sessions,
                               report=latest_report,
                               score_to_label=score_to_label)

@app.route("/student/<int:student_id>")
@login_required
def student_detail(student_id):
    if current_user.role != "teacher":
        return redirect(url_for("dashboard"))
    student = User.query.get_or_404(student_id)
    sessions = (DBSession.query
                .filter_by(user_id=student_id)
                .order_by(DBSession.date.desc())
                .all())
    latest_report = (ProgressReport.query
                     .filter_by(user_id=student_id)
                     .order_by(ProgressReport.report_number.desc())
                     .first())
    return render_template("student_detail.html",
                           student=student,
                           sessions=sessions,
                           report=latest_report,
                           score_to_label=score_to_label)

# ── Routes: Conversation ──────────────────────────────────────────────────────
@app.route("/chat")
@login_required
def chat():
    topic = random.choice(TOPICS)
    session["topic_name"]    = topic["name"]
    session["topic_opening"] = topic["opening"]
    session["turns"]         = []
    session["turn_count"]    = 0
    session["history"]       = []
    return render_template("chat.html",
                           topic=topic["name"],
                           opening=topic["opening"],
                           opening_audio=make_audio_b64(topic["opening"]))

@app.route("/chat/respond", methods=["POST"])
@login_required
def chat_respond():
    data          = request.get_json()
    student_text  = data.get("text", "").strip()
    if not student_text:
        return jsonify({"error": "No text provided"}), 400

    history       = session.get("history", [])
    topic_name    = session.get("topic_name", "")
    turn_count    = session.get("turn_count", 0)
    turns         = session.get("turns", [])
    last_question = data.get("last_question", "")

    # agent now returns (comment, suggestion, question)
    comment, suggestion, question = get_conversation_response(
        student_text, history, topic_name
    )

    # Store turn — suggestion saved directly, no parsing needed later
    turn_data = {
        "app_question":    last_question,
        "student_speech":  student_text,
        "fluency_comment": comment,
        "suggestion":      suggestion,
    }
    turns.append(turn_data)
    turn_count += 1

    history.append({"role": "student",   "content": student_text})
    history.append({"role": "assistant", "content": comment})

    session["turns"]      = turns
    session["turn_count"] = turn_count
    session["history"]    = history

    is_last        = turn_count >= MAX_TURNS
    comment_audio  = make_audio_b64(comment)
    question_audio = make_audio_b64(question) if not is_last else None

    if is_last:
        closing       = "Great conversation! Let me save your session and prepare your fluency practice."
        closing_audio = make_audio_b64(closing)
        return jsonify({
            "comment":       comment,
            "comment_audio": comment_audio,
            "is_last":       True,
            "closing":       closing,
            "closing_audio": closing_audio,
        })

    return jsonify({
        "comment":        comment,
        "comment_audio":  comment_audio,
        "question":       question,
        "question_audio": question_audio,
        "is_last":        False,
    })

@app.route("/chat/transcribe", methods=["POST"])
@login_required
def chat_transcribe():
    audio_data = request.data
    if not audio_data:
        return jsonify({"error": "No audio"}), 400
    try:
        text = transcribe(audio_data)
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat/finish", methods=["POST"])
@login_required
def chat_finish():
    turns      = session.get("turns", [])
    topic_name = session.get("topic_name", "")

    if not turns:
        return jsonify({"error": "No turns to save"}), 400

    session_count  = DBSession.query.filter_by(user_id=current_user.id).count()
    session_number = session_count + 1

    db_session = DBSession(
        user_id        = current_user.id,
        topic          = topic_name,
        session_number = session_number,
    )
    db.session.add(db_session)
    db.session.flush()

    for i, t in enumerate(turns, 1):
        turn = Turn(
            session_id      = db_session.id,
            turn_number     = i,
            app_question    = t["app_question"],
            student_speech  = t["student_speech"],
            fluency_comment = t["fluency_comment"],
        )
        db.session.add(turn)

    analysis_data = analyze_session(turns)
    analysis = SessionAnalysis(
        session_id       = db_session.id,
        vocabulary_score = analysis_data.get("vocabulary_score"),
        vocabulary_note  = analysis_data.get("vocabulary_note"),
        phrasing_score   = analysis_data.get("phrasing_score"),
        phrasing_note    = analysis_data.get("phrasing_note"),
        structure_score  = analysis_data.get("structure_score"),
        structure_note   = analysis_data.get("structure_note"),
        overall_score    = analysis_data.get("overall_score"),
        overall_note     = analysis_data.get("overall_note"),
        suggestion       = analysis_data.get("suggestion"),
    )
    db.session.add(analysis)
    db.session.commit()

    progress_report_data = None
    if session_number % 5 == 0:
        last_5 = (DBSession.query
                  .filter_by(user_id=current_user.id)
                  .order_by(DBSession.session_number.desc())
                  .limit(5).all())
        sessions_data = []
        for s in reversed(last_5):
            if s.analysis:
                sessions_data.append({
                    "topic":            s.topic,
                    "vocabulary_score": s.analysis.vocabulary_score,
                    "vocabulary_note":  s.analysis.vocabulary_note,
                    "phrasing_score":   s.analysis.phrasing_score,
                    "phrasing_note":    s.analysis.phrasing_note,
                    "structure_score":  s.analysis.structure_score,
                    "structure_note":   s.analysis.structure_note,
                    "overall_score":    s.analysis.overall_score,
                    "overall_note":     s.analysis.overall_note,
                })

        if sessions_data:
            report_data   = analyze_progress(sessions_data)
            report_number = (ProgressReport.query
                             .filter_by(user_id=current_user.id)
                             .count()) + 1
            report = ProgressReport(
                user_id                 = current_user.id,
                report_number           = report_number,
                sessions_from           = session_number - 4,
                sessions_to             = session_number,
                vocabulary_score        = report_data.get("vocabulary_score"),
                vocabulary_label        = score_to_label(report_data.get("vocabulary_score", 5)),
                vocabulary_description  = report_data.get("vocabulary_description"),
                phrasing_score          = report_data.get("phrasing_score"),
                phrasing_label          = score_to_label(report_data.get("phrasing_score", 5)),
                phrasing_description    = report_data.get("phrasing_description"),
                structure_score         = report_data.get("structure_score"),
                structure_label         = score_to_label(report_data.get("structure_score", 5)),
                structure_description   = report_data.get("structure_description"),
                overall_score           = report_data.get("overall_score"),
                overall_label           = score_to_label(report_data.get("overall_score", 5)),
                improvement_description = report_data.get("improvement_description"),
            )
            db.session.add(report)
            db.session.commit()
            progress_report_data = report_data

    # Build review turns — suggestion already stored, no parsing needed
    review_turns = []
    for t in turns:
        question   = t["app_question"] or ""
        suggestion = t["suggestion"] or t["student_speech"]
        review_turns.append({
            "question":         question,
            "question_audio":   make_audio_b64(question) if question else "",
            "speech":           t["student_speech"],
            "comment":          t["fluency_comment"],
            "suggestion":       suggestion,
            "suggestion_audio": make_audio_b64(suggestion),
        })

    return jsonify({
        "review_turns":    review_turns,
        "analysis":        analysis_data,
        "progress_report": progress_report_data,
        "session_number":  session_number,
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
