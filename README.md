# 🔍 InfoFetch AI — Intelligent Research Platform

> AI-powered company intelligence and market research, built for professionals who demand excellence.

![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?style=flat-square&logo=streamlit)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5--turbo-green?style=flat-square&logo=openai)
![LangChain](https://img.shields.io/badge/LangChain-Latest-yellow?style=flat-square)
![Razorpay](https://img.shields.io/badge/Payments-Razorpay-blue?style=flat-square)

---

## 📌 What is InfoFetch AI?

InfoFetch AI is a full-stack AI research platform that lets users instantly research companies, job markets, salaries, and general topics using a combination of real-time web search and GPT-3.5-turbo. It features a dual-mode interface — a **deep research engine** for structured reports and an **AI chatbot** for quick conversational Q&A.

---

## ✨ Features

### 🏢 Company Intelligence
- Full company profiles: CEO, founding year, headquarters, revenue, employee count
- Contact information: official email, phone, address, LinkedIn, careers page
- Career opportunities: entry-level roles, required skills, salary ranges, hiring status
- Work culture: environment, perks, and company values

### 🔍 General Research Engine
- Multi-source web search via SerpAPI (5 targeted queries per research)
- AI-structured output with overview, key insights, expert analysis, and sources
- Confidence scoring (High / Medium / Low)

### 💬 AI Chatbot
- Conversational Q&A powered by `gpt-3.5-turbo`
- Persistent chat history saved to database
- Smart routing — quick questions answered inline, complex queries redirected to research
- Supports greetings, follow-ups, and contextual conversation

### 📚 Search History
- Full history of past research saved per user
- Re-view, re-run, or delete individual searches
- Stats dashboard: total searches, chat messages, average confidence

### 💳 Subscription Plans & Payments
| Plan     | Price     | Searches/Day | Features                        |
|----------|-----------|---------------|---------------------------------|
| Free     | $0        | 10            | Basic research, community support |
| Plus ⭐   | ₹19/month | 100           | Advanced insights, PDF export    |
| Premium 👑| ₹49/month | Unlimited     | API access, team collaboration   |

Payments are processed securely via **Razorpay**.

### 🌟 Feedback System
- Multi-dimensional rating: overall experience, accuracy, speed, UI
- Feature request tracking
- Public testimonials toggle
- Feedback feeds directly into the landing page reviews section

---

## 🛠️ Tech Stack

| Layer         | Technology                          |
|---------------|--------------------------------------|
| Frontend      | Streamlit (custom CSS, Space Grotesk / Inter fonts) |
| AI Models     | OpenAI GPT-3.5-turbo (research + chat) |
| Search        | SerpAPI via LangChain `SerpAPIWrapper` |
| Orchestration | LangChain (`langchain-openai`, `langchain-community`) |
| Database      | SQLite (users, search history, chat, payments, feedback) |
| Payments      | Razorpay (INR, test + live mode)     |
| Auth          | Username/password with DB verification |

---

## 📁 Project Structure

```
InfoFetch-AI/
├── app.py                  # Main Streamlit app — all pages & UI
├── serp.py                 # Core AI engine — research, chatbot, LLM calls
├── db_utils.py             # Database helpers — users, history, feedback, payments
├── razorpay_handler.py     # Razorpay order creation & signature verification
├── migrate_db.py           # One-time DB migration script (adds 'plan' column)
├── api.env                 # 🔒 API keys (NOT committed to git — see setup)
├── api.env.example         # Template for required environment variables
├── requirements.txt        # Python dependencies
└── infofetch_ai.db         # SQLite database (auto-created on first run)
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/shashwatshekhar06-gif/InfoTech-AI.git
cd InfoTech-AI
```

### 2. Create a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

Create an `api.env` file in the project root (this file is gitignored):

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
SERPAPI_API_KEY=your-serpapi-key-here
RAZORPAY_KEY_ID=rzp_test_your-key-id
RAZORPAY_KEY_SECRET=your-razorpay-secret
```

> ⚠️ **Never commit `api.env` to git.** It is listed in `.gitignore` for this reason.

### 5. Run database migration (first time only)

```bash
python migrate_db.py
```

### 6. Launch the app

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 🔑 Demo Accounts

| Username   | Password      | Plan   |
|------------|---------------|--------|
| admin      | secure123     | Free   |
| researcher | research2024  | Free   |
| analyst    | analyst2024   | Free   |
| manager    | manager2024   | Free   |
| executive  | exec2024      | Free   |

---

## 🧠 How the Research Engine Works

1. **Query Classification** — Detects whether the query is about a company or a general topic using keyword matching and regex patterns
2. **Company Name Extraction** — Identifies the target company from known lists and NLP patterns
3. **Targeted Web Searches** — Runs 5 parallel SerpAPI queries covering: contact info, careers, company overview, LinkedIn, and salary/culture
4. **LLM Extraction** — GPT-3.5-turbo (JSON mode, temperature=0.1) extracts structured data from search results
5. **Post-Processing** — Fills any remaining unknown fields using pattern-based URL construction and known company data
6. **Fallback Handling** — If JSON parsing fails, a smart fallback extracts key data from raw search results

---

## 🔒 Security Notes

- API keys are loaded from `api.env` using `python-dotenv` — never hardcoded
- `api.env` is listed in `.gitignore` — should never be committed
- Razorpay payments use HMAC-SHA256 signature verification
- All user passwords should be hashed in production (see `db_utils.py`)

---

## 📦 Requirements

```
streamlit
langchain
langchain-openai
langchain-community
openai
google-search-results   # SerpAPI
razorpay
python-dotenv
```

Install all with:

```bash
pip install -r requirements.txt
```

---

## 🗺️ Roadmap

- [ ] Mobile-responsive layout
- [ ] PDF export of research reports
- [ ] Bulk research mode
- [ ] Email digest / alerts
- [ ] REST API for external integrations
- [ ] Multi-language support
- [ ] Visual charts and graphs for data
- [ ] CRM integrations (HubSpot, Salesforce)

---

## 🙌 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

---

## 📄 License

MIT License — see `LICENSE` for details.

---

## 👨‍💻 Author

Built by **Shashwat Shekhar**  
GitHub: [@shashwatshekhar06-gif](https://github.com/shashwatshekhar06-gif)

---

*Powered by OpenAI • SerpAPI • Streamlit • Razorpay*
