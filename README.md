# 🤖 AI TASKFORCE

**A Multi-Agent Desktop Automation Platform**

AI TASKFORCE is a desktop application that unifies **five AI-powered business
automation agents** under one dashboard. It is built with Python and PyQt6, runs
its core AI locally for privacy, and is designed to be free to operate.

Final Year Project — B.E. Software Engineering, Air University (Karachi Campus).

---

## ✨ Features

| Agent | What it does |
|-------|--------------|
| ✉️ **Email Agent** | Generates tone-controlled emails with a local LLM and sends them in bulk over SMTP. |
| 📝 **Content Scripting Agent** | Generates blogs, social captions, and ad copy on demand. |
| 📧 **Email Scraper Agent** | Finds business leads by keyword + city (Google Maps + website crawling). |
| 🛒 **Product Hunter Agent** | Finds trending products and ranks them by a transparent opportunity score. |
| 🎙️ **Voice Agent** | Answers **real phone calls** — schedules meetings against Google Calendar and answers caller questions from uploaded documents (RAG). |

---

## 🧱 Tech Stack

- **Language:** Python 3.11
- **Desktop UI:** PyQt6
- **Local AI:** Ollama (for the Email & Content agents)
- **Cloud AI (Voice Agent):** Groq (fast Llama inference + Whisper STT)
- **Scraping:** Playwright (Google Maps) + BeautifulSoup (websites)
- **Voice telephony:** Twilio
- **Voice backend:** FastAPI + Uvicorn (webhook server), exposed with ngrok
- **Scheduling:** Google Calendar API
- **RAG:** ChromaDB + sentence-transformers
- **Data/Export:** pandas + openpyxl

---

## 📁 Project Structure

```
FYP/
├── app.py                     # Main application entry point
├── dashboard/                 # Main window, dashboard, global styles
├── emailagent/                # Email Agent
├── contentscripting/          # Content Scripting Agent
├── emailscraper/              # Email Scraper Agent
├── producthunter2/            # Product Hunter Agent
├── voiceagent/                # Voice Agent (phone, calendar, RAG)
│   ├── voice_server.py        # FastAPI webhook for Twilio calls
│   ├── voiceagent_page.py     # Dashboard card (analytics, uploads)
│   ├── core/                  # brain, calendar, email, RAG, intent, contacts
│   ├── uploads/               # Owner's documents for RAG (git-ignored)
│   └── data/                  # Local DB, analytics, settings (git-ignored)
├── shared/                    # Ollama client, settings, themes
└── requirements.txt
```

---

## 🚀 Getting Started

### 1. Prerequisites

Install these on your machine first:

- **Python 3.11** — https://www.python.org/downloads/
- **Ollama** — https://ollama.com/  (for the Email & Content agents)
- **Git** — https://git-scm.com/

### 2. Clone the repository

```bash
git clone https://github.com/KHUBAIB-MEO/FYP.git
cd FYP
```

### 3. Create a virtual environment & install dependencies

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Install the Playwright browser (for the Email Scraper)

```bash
playwright install chromium
```

### 5. Set up Ollama (for Email & Content agents)

```bash
# After installing Ollama, pull a model:
ollama pull qwen2.5
```
Make sure Ollama is running in the background.

---

## 🎙️ Voice Agent Setup (optional but recommended)

The Voice Agent needs a few free external services. Skip this section if you
only want the four desktop agents.

### A. Groq API key (the AI brain)

1. Sign up at **https://console.groq.com**
2. Go to **API Keys → Create API Key**, copy the `gsk_...` key.

### B. Gmail app password (for sending approval emails)

1. Enable **2-Step Verification** at https://myaccount.google.com/security
2. Create an app password at https://myaccount.google.com/apppasswords
3. Copy the 16-character password (remove spaces).
4. Enable **IMAP** in Gmail settings (so the agent can read YES/NO replies).

### C. Google Calendar API (for scheduling)

1. Go to **https://console.cloud.google.com** → create a project.
2. **APIs & Services → Library →** enable **Google Calendar API**.
3. **OAuth consent screen →** External → add yourself as a **Test user**.
4. **Credentials → Create Credentials → OAuth client ID → Desktop app**.
5. **Download JSON**, rename it to `credentials.json`, place it in `voiceagent/`.
6. Set your Google Calendar's timezone to your local zone (e.g. Asia/Karachi).

### D. Twilio (for real phone calls)

1. Sign up at **https://www.twilio.com/try-twilio** (free trial with credit).
2. **Verify your own phone number** (Phone Numbers → Verified Caller IDs →
   "Call me" if SMS is restricted in your country).
3. **Buy a phone number** (Phone Numbers → Buy a number; choose one with Voice).
4. From the Console dashboard, copy your **Account SID**, **Auth Token**, and
   **Twilio number**.

> **Note on trial accounts:** you can only call *from* your verified number, and
> SMS/calls are limited to verified numbers. Upgrading removes these limits.

### E. ngrok (exposes your local server to Twilio)

1. Sign up at **https://ngrok.com** (free), download ngrok, unzip it.
2. Add your authtoken:
   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN
   ```

### F. Create your `.env` file

Copy `voiceagent/.env.example` to `voiceagent/.env` and fill in your values:

```
GROQ_API_KEY=gsk_your_key
GMAIL_ADDRESS=your_business_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
ASSISTANT_EMAIL=assistant_who_approves@gmail.com
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_NUMBER=+1XXXXXXXXXX
```

> ⚠️ **Never commit your `.env` file.** It is git-ignored by default. Each
> developer/owner supplies their own credentials.

---

## ▶️ Running the Application

### The desktop app (all agents' dashboard)

```bash
python app.py
```

### The Voice Agent phone server (run alongside the app)

The Voice Agent needs its webhook server and a public tunnel running.

**Terminal 1 — start the voice server:**
```bash
uvicorn voiceagent.voice_server:app --port 8000
```

**Terminal 2 — expose it with ngrok:**
```bash
ngrok http 8000
```
Copy the `https://xxxx.ngrok-free.dev` URL that ngrok prints.

**Connect Twilio to your server:**
1. Twilio Console → Phone Numbers → your number.
2. **Voice Configuration → A call comes in →** Webhook,
   URL = `https://xxxx.ngrok-free.dev/voice`, method **HTTP POST**. Save.
3. **Messaging Configuration → A message comes in →** Webhook,
   URL = `https://xxxx.ngrok-free.dev/sms`, method **HTTP POST**. Save.

> Every time you restart ngrok, the URL changes — update both webhook URLs.

**Now call your Twilio number** from your verified phone and talk to the agent!

---

## 🗣️ Using the Voice Agent

Once connected, callers can:
- **Ask a question** — *"What are your office hours?"* (answered from uploaded docs)
- **Book a meeting** — *"Book a meeting Monday at 3pm"* (checked against the calendar)
- **Say goodbye** — ends the call

Meetings go through an **approval flow**: the assistant gets an email, replies
**YES** or **NO**, and the caller is emailed the result.

The owner manages everything from the **Voice Agent card** on the dashboard:
- View analytics (calls handled, meetings booked, questions answered)
- Upload PDF/DOCX/TXT documents for the knowledge base
- Set the assistant's approval email

---

## 🔒 Privacy & Security Notes

- The Email & Content agents run AI **locally** via Ollama — no data leaves your machine.
- Secrets live only in `.env` (git-ignored). Never commit credentials.
- `credentials.json` and `token.json` (Google auth) are git-ignored.
- Each deployment/owner supplies their own API keys and email credentials.

---

## ⚠️ Known Limitations

- Free API tiers have request limits (Groq ~30 req/min; RapidAPI ~100 req/month).
- Twilio trial restricts calls/SMS to verified numbers; upgrading removes this.
- Capturing an email by voice is unreliable, so the Voice Agent identifies known
  callers by phone number and falls back to SMS, then voice with confirmation.
- Heavy scraping may trigger a CAPTCHA, which is detected and reported.

---

## 👤 Author

**Khubaib** — Student ID 15045
B.E. Software Engineering, Air University (Karachi Campus)

---

## 📄 License

This project was developed for academic purposes as a Final Year Project.
