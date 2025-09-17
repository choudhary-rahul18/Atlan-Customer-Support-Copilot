# Atlan Customer Support Copilot  
An end to end **AI-powered customer support system** combining **Hybrid RAG-based answers**, **ticket escalation**, and **session-aware chat**  served by a **FastAPI backend** and a **Streamlit frontend**.  

---

##  What’s Inside  
- **Backend API** with LLM planning, RAG retrieval, and ticket workflows  
- **Streamlit chat UI** with session management and dashboards  
- **Excel-based storage** for tickets, chat history, and KB source  
- **Clean, reproducible setup** using a virtual environment  

---
## Capabilities of Customer Support Copilot
- Understands what customers actually mean using chat history
- Detects emotions like frustrated, curious, angry, or neutral
- Adjusts responses based on customer mood with empathy or professionalism
- Instantly identifies when customers are asking about a ticket
- Differentiates between current tickets and older tickets
- Provides quick status updates without repeated details
- Recognizes urgent cases and escalates to senior agents when needed
- Answers questions by pulling information from the company’s database or FAQs
- Provides accurate and up-to-date responses instantly
- Automatically chooses the best response: ticket update, escalation, or information

---
## Capabilities of Support Ticket Dashboard 
- Displays a centralized view of all support tickets in a clean, modern interface
- Allows real-time tracking of tickets to monitor progress
- Provides easy-to-read ticket cards with query details and status highlights
- Includes search and filtering options (via pandas/streamlit integration) for faster access
- Tracks timestamps to show when tickets were created and updated
- Supports data-driven insights by loading ticket data from spreadsheets/databases

---
## Capabilities of Chat History Dashboard
- Provides a centralized dashboard to view all past chat conversations
- Displays per-chat transcripts with clear, expandable details
- Uses Chat ID as a reference for organizing and tracking conversations
- Allows quick searching and filtering of chat sessions
- Shows conversation “turns” to highlight how the interaction flowed
- Presents data in a professional, clean interface with a wide layout
- Helps support teams revisit, analyze, and resolve recurring issues

---
##  Project Structure  

```text
Atlan Customer Support Copilot/
├── backend.py                     # FastAPI backend (LLM, RAG, tickets)
├── Customer_Support_Copilot.py    # Streamlit frontend (main app)
├── rag.py                         # RAG pipeline
├── database.py                    # Ticket + history persistence
├── prompts.py                     # Prompt templates
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
```

## 2) Environment Variables

- Create a .env file in the project root with:
- OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
- **Tips**:
  - Keep .env out of version control.
  - Provide a .env.example for collaborators with placeholder values.
##  3) Data Files
- Ensure the files/ directory contains:
- files/sample1.xlsx → Knowledge base for RAG
- files/tickets.xlsx → Tickets store
- files/chat_history.xlsx → Chat history store



## 5) Collaborator Setup Guide
#### For teammates setting this up locally:
 - Clone/download the repository to a local folder.
 - Create a virtual environment inside the project and activate it:

 - python -m venv venv
```python
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate
Install dependencies from requirements.txt:
pip install --upgrade pip
pip install -r requirements.txt
```
  -**Start backend**:
  - python -m uvicorn backend:app --reload
  - API docs: http://localhost:8000/docs
  - Health: http://localhost:8000/health
  - Status: http://localhost:8000/status

  - Create a .env in the project root and add:
   #text
    - OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

- Ensure the files/ directory exists and includes:
  - sample1.xlsx
  - tickets.xlsx (columns: ticket_id, chat_id, subject, status, query, response, time)
  - chat_history.xlsx
  
- Start the backend using the module form (ensures the venv interpreter is used):
```python
python -m uvicorn backend:app --reload
```

- Start the frontend in a second terminal (with the same venv activated):
```python
streamlit run Customer_Support_Copilot.py
```

- Use the “New Session” button to create a fresh chat_id and clear history.
- If switching LLMs, only update the import and constructor in backend.py → BackendState._initialize_llm and add the provider’s env vars to .env. Do not change prompt or chain code.


##  6) API Quick Reference
```bash
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
```

## 7) Common Issues & Troubleshooting
- “ModuleNotFoundError: No module named ‘langchain_openai’”
  - Ensure venv is activated.
  - Use: python -m uvicorn backend:app --reload
  - Reinstall in venv: pip install langchain-openai
- “OpenAI key not found”
  - Confirm .env exists in project root.
  - Ensure OPENAI_API_KEY is properly set.
  - Restart the backend after setting .env.
- Excel file “permission denied”
  - Close the file if opened in Excel.
  - Ensure paths are correct and writable.
- Frontend loads but backend offline
  - Start backend first.
  - Verify http://localhost:8000/health returns status.
  - Check terminal logs for initialization errors (LLM/RAG).


## 8) Configuration Notes

- Ticket store path: files/tickets.xlsx (set in backend constants)
- RAG data: Reads files/sample1.xlsx and precomputes chunks/embeddings
- Link formatting: References appended as Markdown (max 3 sources)

## 9) Quick Commands Cheat Sheet
```python
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
```
