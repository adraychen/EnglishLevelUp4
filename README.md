# 🎓 English Fluency Coach

An AI-powered English fluency coaching web app that helps non-native speakers sound more natural in everyday conversation. Students have real conversations with an AI coach, receive fluency feedback, and practice shadowing — all through voice or text.

---

## Features

### For Students
- **Voice or text input** — speak or type your answers
- **Real conversations** — AI coach picks a random everyday topic and chats naturally
- **Fluency feedback** — after each response, the coach suggests a more natural way to say it
- **Fluency practice (shadowing)** — after 5 conversation turns, practice saying the suggested answers out loud and compare what you said
- **Progress dashboard** — view session history and fluency scores
- **Progress reports** — generated every 5 sessions with scores and descriptions across vocabulary, phrasing, and sentence structure

### For Teachers
- **Student dashboard** — see all students with their latest fluency scores and labels
- **Individual student view** — drill into any student's session history, progress report, and suggestions

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask (Python) |
| Database | PostgreSQL (Supabase) |
| Auth | Flask-Login + bcrypt |
| AI conversation | CrewAI + Groq (llama-4-scout) |
| Speech-to-text | Groq Whisper turbo |
| Text-to-speech | gTTS |
| Hosting | Render.com |

---

## Project Structure

```
fluency-coach/
├── app.py                      # Flask routes and main application
├── agent.py                    # CrewAI agents for conversation and analysis
├── models.py                   # SQLAlchemy database models
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render deployment configuration
├── .env.example                # Example environment variables
├── .gitignore
└── templates/
    ├── base.html               # Base layout
    ├── login.html              # Login page
    ├── register.html           # Registration page
    ├── chat.html               # Conversation and fluency practice
    ├── student_dashboard.html  # Student progress dashboard
    ├── teacher_dashboard.html  # Teacher overview of all students
    └── student_detail.html     # Teacher view of individual student
```

---

## Database Schema

| Table | Description |
|---|---|
| `users` | Students and teachers with roles |
| `sessions` | Each conversation session per user |
| `turns` | Each question/answer turn within a session |
| `session_analysis` | AI fluency analysis scores after each session |
| `progress_reports` | Aggregated progress report generated every 5 sessions |

---

## Getting Started

### Prerequisites
- Python 3.11
- A [Groq](https://console.groq.com) API key (free)
- A [Supabase](https://supabase.com) project (free)

### Local Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/yourusername/fluency-coach.git
   cd fluency-coach
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** based on `.env.example`
   ```
   GROQ_API_KEY=your_groq_api_key
   SECRET_KEY=any_random_string
   DATABASE_URL=postgresql://user:password@host/dbname
   ```

4. **Run the app**
   ```bash
   python app.py
   ```

5. Open `http://localhost:5000` in your browser

---

## Deploying to Render

1. Push the repo to GitHub
2. Go to [render.com](https://render.com) → **New** → **Web Service**
3. Connect your GitHub repo
4. Set the following environment variables in Render's dashboard:
   - `GROQ_API_KEY` — your Groq API key
   - `SECRET_KEY` — any long random string
   - `DATABASE_URL` — your Supabase connection string
5. Set **Start Command** to:
   ```
   gunicorn app:app --bind 0.0.0.0:$PORT
   ```
6. Set **Python version** to `3.11` (add a `.python-version` file with `3.11`)
7. Deploy — the app creates all database tables automatically on first start

---

## Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key for LLM and Whisper |
| `SECRET_KEY` | Flask session secret key |
| `DATABASE_URL` | PostgreSQL connection string |

---

## Conversation Topics

The app randomly selects from 15 everyday topics including:
- Weekend plans
- Talking about food or restaurants
- Catching up with a friend
- Talking about a movie or TV show
- Health and exercise
- Shopping, hobbies, travel, and more

---

## Fluency Scoring

Each session is analyzed across three categories:

| Category | What it measures |
|---|---|
| Vocabulary | Word choice, range, and appropriateness |
| Phrasing | Natural expression and conversational flow |
| Structure | Sentence construction and clarity |

Scores are on a 1–10 scale with labels:

| Score | Label |
|---|---|
| 1–3 | Beginner |
| 4–5 | Developing |
| 6–7 | Intermediate |
| 8–9 | Fluent |
| 10 | Mastery |

A progress report comparing the last 5 sessions is generated automatically every 5 sessions.

---

## License

MIT
