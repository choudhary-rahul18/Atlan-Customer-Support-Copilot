Here’s the complete README.md:
# Atlan Customer Support Copilot  

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)  
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)  
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io/)  
[![LangChain](https://img.shields.io/badge/LangChain-0.2+-purple.svg)](https://www.langchain.com/)  

An end-to-end **AI-powered customer support system** combining **RAG-based answers**, **ticket escalation**, and **session-aware chat** — served by a **FastAPI backend** and a **Streamlit frontend**.  

---

##  What’s Inside  
- **Backend API** with LLM planning, RAG retrieval, and ticket workflows  
- **Streamlit chat UI** with session management and dashboards  
- **Excel-based storage** for tickets, chat history, and KB source  
- **Clean, reproducible setup** using a virtual environment  

---

##  Project Structure  

```text
Atlan Customer Support Copilot/
├── backend.py                     # FastAPI backend (LLM, RAG, tickets)
├── Customer_Support_Copilot.py    # Streamlit frontend (main app)
├── rag.py                         # RAG pipeline (embeddings, FAISS, BM25)
├── database.py                    # Ticket + history persistence (Excel)
├── prompts.py                     # Prompt templates (Master, RAG, Ticket, etc.)
├── requirements.txt               # Python dependencies
├── .env                           # Environment variables (OPENAI_API_KEY)
├── pages/                         # Frontend dashboards
│   ├── Support_Tickets_Dashboard.py
│   └── Chat_History_Dashboard.py
├── files/                         # App data (make sure these exist)
│   ├── sample1.xlsx               # Knowledge base (source for RAG)
│   ├── tickets.xlsx               # Tickets database
│   └── chat_history.xlsx          # Chat history database
└── venv/                          # Virtual environment (recommended)
```

---

##  Prerequisites  
- Python **3.8+** installed  
- An **OpenAI API key**  

---

##  1) Setup (Recommended: Virtual Environment)  

```bash
# 1. Navigate to the project directory
cd "Atlan Customer Support Copilot"

# 2. Create and activate a virtual environment
python -m venv venv

# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
## 2) Environment Variables
Create a .env file in the project root with:
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Tips:
Keep .env out of version control.
Provide a .env.example for collaborators with placeholder values.
##  3) Data Files
Ensure the files/ directory contains:
files/sample1.xlsx → Knowledge base for RAG
files/tickets.xlsx → Tickets store
files/chat_history.xlsx → Chat history store

## 4) Common Issues & Troubleshooting
“ModuleNotFoundError: No module named ‘langchain_openai’”
Ensure venv is activated
Use: python -m uvicorn backend:app --reload
Reinstall in venv: pip install langchain-openai
“OpenAI key not found”
Confirm .env exists in project root
Ensure OPENAI_API_KEY is properly set
Restart the backend
Excel file “permission denied”
Close the file if opened in Excel
Ensure paths are correct and writable
Frontend loads but backend offline
Start backend first
Verify http://localhost:8000/health
Check terminal logs for initialization errors (LLM/RAG)

##  5) Recommended Workflow for Collaborators
Clone or download the project
Create and activate a virtual environment
Install dependencies: pip install -r requirements.txt
Add .env with OPENAI_API_KEY
Ensure files/ contains: sample1.xlsx, tickets.xlsx, chat_history.xlsx
Start backend:
python -m uvicorn backend:app --reload
API docs: http://localhost:8000/docs
Health: http://localhost:8000/health
Status: http://localhost:8000/status
Start frontend:
streamlit run Customer_Support_Copilot.py
Use the “New Session” button to generate a fresh chat_id
Check dashboards under /pages

##  6) LLM Usage Policy (Read Before Changing Models)
Golden Rule: Always use LangChain chat model integrations.
Do not switch to raw provider SDKs — this requires major changes in prompts, chain code, and output parsing.
To switch providers, update only:
File: backend.py
Class: BackendState
Method: _initialize_llm(self)
Provider examples:
OpenAI (default)
from langchain_openai import ChatOpenAI
self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.5)
.env: OPENAI_API_KEY
Azure OpenAI
from langchain_openai import AzureChatOpenAI
self.llm = AzureChatOpenAI(
    azure_deployment="YOUR_DEPLOYMENT_NAME",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    temperature=0.5,
)
.env: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION
Anthropic (Claude)
from langchain_anthropic import ChatAnthropic
self.llm = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0.5)
.env: ANTHROPIC_API_KEY
Google (Gemini)
from langchain_google_genai import ChatGoogleGenerativeAI
self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.5)
.env: GOOGLE_API_KEY
Mistral
from langchain_mistralai import ChatMistralAI
self.llm = ChatMistralAI(model="mistral-large-latest", temperature=0.5)
.env: MISTRAL_API_KEY
Groq
from langchain_groq import ChatGroq
self.llm = ChatGroq(model="llama3-70b-8192", temperature=0.5)
.env: GROQ_API_KEY
Together AI
from langchain_together import ChatTogether
self.llm = ChatTogether(model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", temperature=0.5)
.env: TOGETHER_API_KEY
Local Ollama
from langchain_ollama import ChatOllama
self.llm = ChatOllama(model="llama3.1", base_url=os.getenv("OLLAMA_HOST","http://localhost:11434"), temperature=0.5)
.env: OLLAMA_HOST (default: http://localhost:11434)
OpenAI-Compatible Servers (vLLM, LM Studio, TGI, llama.cpp)
from langchain_openai import ChatOpenAI
self.llm = ChatOpenAI(
    model="mistral:latest",
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY","not-needed"),
    temperature=0.5,
)
.env: OPENAI_BASE_URL, OPENAI_API_KEY (dummy if server doesn’t enforce auth)
Restart after changes:
python -m uvicorn backend:app --reload

## 7) Collaborator Setup Guide
Clone/download repository locally
Create & activate venv
Install dependencies with pip install -r requirements.txt
Create .env file with:
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Ensure files/ contains:
sample1.xlsx
tickets.xlsx (columns: ticket_id, chat_id, subject, status, query, response, time)
chat_history.xlsx (columns: chat_id, timestamp, role, content, type)
Start backend:
python -m uvicorn backend:app --reload
Start frontend:
streamlit run Customer_Support_Copilot.py
Use “New Session” to create a fresh chat_id

##  8) API Quick Reference
Base URL: http://localhost:8000
GET /health → Basic heartbeat with uptime
GET /status → LLM/RAG/DB flags + timestamp
GET /welcome → Random welcome message
POST /query → Processes user message
{
  "query": "How to authenticate?",
  "chat_id": "abcd1234",
  "chat_history": [
    { "role": "user", "content": "Hello", "timestamp": "10:05:10", "type": "user_input" }
  ]
}
GET /tickets/{chat_id} → Returns ticket metadata
POST /sessions/persist → Persists chat history
{ "chat_id": "abcd1234", "chat_history": [ ... ] }
⚠️ 9) Common Issues & Troubleshooting (Duplicate Section for Quick Access)
(Same as section 4, repeated intentionally for easy lookup).
⚙️ 10) Configuration Notes
Ticket store path: files/tickets.xlsx (set in backend constants)
RAG data: Reads files/sample1.xlsx and precomputes chunks/embeddings
Link formatting: References appended as Markdown (max 3 sources)
📝 11) Quick Commands Cheat Sheet
# Create venv and install
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run backend (always use -m to ensure venv interpreter)
python -m uvicorn backend:app --reload

# Run frontend
streamlit run Customer_Support_Copilot.py

# Regenerate requirements
pip freeze > requirements.txt

# Clean and rebuild venv (if needed)
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
