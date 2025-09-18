# streamlit run Customer_Support_Copilot.py
import streamlit as st
import requests, time
import uuid
from datetime import datetime
import json, logging, sys, random

# Configuration
API_BASE_URL = "http://localhost:8000"

# Streamlit page config
st.set_page_config(
    page_title="AI Chatbot", 
    page_icon="🤖", 
    layout="centered"
)

if "logger_init" not in st.session_state:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    st.session_state.logger_init = True
log = logging.getLogger("chat")

# Enhanced CSS with Atlan-themed header
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(135deg, #1e3a8a, #7c3aed, #a855f7);
        color: white;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .status-indicator {
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        text-align: center;
    }
    .status-online { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .status-offline { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .session-info {
        background: #e3f2fd;
        padding: 0.8rem;
        border-radius: 8px;
        border-left: 4px solid #2196F3;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# API Client Class
class ChatbotAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30
    
    def check_health(self):
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
    
    def send_message(self, query: str, chat_id: str, chat_history: list):
        try:
            formatted_history = []
            for msg in chat_history:
                formatted_history.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg.get("timestamp", ""),
                    "type": msg.get("type", "")
                })
            
            payload = {
                "query": query,
                "chat_id": chat_id,
                "chat_history": formatted_history
            }
            
            response = self.session.post(f"{self.base_url}/query", json=payload)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"API Error: {str(e)}")
            return None
        

def get_welcome_message():
    try:
        response = requests.get(f"{API_BASE_URL}/welcome")
        if response.status_code == 200:
            return response.json().get("message", "")
    except Exception as e:
        log.error(f"Welcome fetch failed: {e}")
    return "👋 Welcome! How can I help you today?"


# Enhanced session state initialization
def initialize_session_state():
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'chat_id' not in st.session_state:
        st.session_state.chat_id = str(uuid.uuid4())[:12]
    
    if 'api_client' not in st.session_state:
        st.session_state.api_client = ChatbotAPI(API_BASE_URL)
    
    if 'session_start_time' not in st.session_state:
        st.session_state.session_start_time = datetime.now()
    
    if 'is_processing' not in st.session_state:
        st.session_state.is_processing = False
    

# Function to restart session
def restart_session():
    """Create a new chat session with fresh chat_id and empty history"""
    new_chat_id = str(uuid.uuid4())[:12]
    old_chat_id = st.session_state.chat_id
    old_message_count = len(st.session_state.chat_history)
    
    st.session_state.chat_id = new_chat_id
    st.session_state.chat_history = []
    st.session_state.session_start_time = datetime.now()
    st.session_state.is_processing = False  # Reset processing state
    
    st.success(f"🔄 New session started! (Previous: {old_chat_id} with {old_message_count} messages)")
    st.rerun()


def persist_history_now():
    try:
        st.session_state.api_client.session.post(
            f"{API_BASE_URL}/sessions/persist",
            json={
                "chat_id": st.session_state.chat_id,
                "chat_history": st.session_state.chat_history
            },
            timeout=10
        )
    except Exception as e:
        # non-blocking
        st.session_state.get("debug", False) and st.warning(f"Persist failed: {e}")

# Main app
def main():
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h2>🤖 Atlan Customer Support Copilot</h2>
        <p>Smart Conversations, Instant Solutions</p>
    </div>
    """, unsafe_allow_html=True)
    
 
    #real-time countdown
    placeholder = st.empty()
    max_wait = 15
    api_online = False
    
    # Count down every second: 15
    for countdown in range(max_wait, 0, -1):
        api_online = st.session_state.api_client.check_health()
    
    # Handle timeout case
    if not api_online:
        placeholder.error("!! Backend API is offline")
            
        st.stop()
    
    # Sidebar
    with st.sidebar:
        if api_online:
            st.markdown("""
            <div class="status-indicator status-online">
                Backend API: Online
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-indicator status-offline">
                ❌ Backend API: Offline
            </div>
            """, unsafe_allow_html=True)
        st.markdown(f"##### Chat Session: `{st.session_state.chat_id}`")

        if st.button("New Session", use_container_width=True, type="primary"):

            # 2) Reset state
            st.session_state.chat_id = str(uuid.uuid4())[:12]
            st.session_state.chat_history = []
            st.session_state.is_processing = False
            st.success("New session started!")
            st.rerun()
        
        # Add vertical space to push disclaimer down
        st.markdown("<div style='height: 30vh;'></div>", unsafe_allow_html=True)
        st.markdown("""
<div style="font-size: 14px,color: #666;">Disclaimer</div>
""", unsafe_allow_html=True)

        st.markdown("""
        <div style="font-size: 14px; color: #666;">
            <small>
            <strong>🤖 AI-Generated Responses</strong><br>
            This chatbot provides AI-generated responses for reference purposes only. Responses may not always be accurate or complete.
            <br>
            <strong>For comprehensive support:</strong><br>
            • Visit the reference links given in response<br>
            • Verify important information independently
            </small>
        </div>
        """, unsafe_allow_html=True)
    
    
    # Main chat interface
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            if message.get("type") == "RAG_Prompt":
                st.info("📚 Knowledge Base")
            elif message.get("type") == "Urgent_ticket":
                st.success("🎫 Ticket Created")
            elif message.get("type") == "Confused_Query":
                st.warning("❓ Help Request")
            elif message.get("type") == "Ticket_Status":
                st.info("ℹ Ticket_Status")
            
            st.write(message["content"])
            
            if message.get("processing_time"):
                st.caption(f"⚡ {message['processing_time']:.2f}s")

    if len(st.session_state.chat_history) == 0:
        with st.chat_message("assistant"):
            st.info("👋 Welcome!")
            welcome_msg = get_welcome_message()
            st.write(welcome_msg)
   
    
    # Chat input - disabled during processing
    prompt = st.chat_input(
        "AI is thinking... Please wait" if st.session_state.is_processing else "Type your message here...",
        disabled=st.session_state.is_processing
    )
    
    # ✅ FIXED: Handle the input properly
    if prompt and not st.session_state.is_processing:
        # Set processing state immediately
        st.session_state.is_processing = True
        
        # Add user message
        user_message = {
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().strftime('%H:%M:%S')
        }
        st.session_state.chat_history.append(user_message)
        persist_history_now()
        
        # Rerun to show disabled input and processing message
        st.rerun()
    
    # Process the message if we're in processing state
    if st.session_state.is_processing and len(st.session_state.chat_history) > 0:
        # Get the last user message
        last_message = st.session_state.chat_history[-1]
        
        # Only process if the last message is from user and we haven't processed it yet
        if last_message["role"] == "user" and not hasattr(st.session_state, 'processing_message_id'):
            st.session_state.processing_message_id = len(st.session_state.chat_history) - 1
            
            with st.chat_message("assistant"):
                with st.spinner("🤖 Thinking..."):
                    result = st.session_state.api_client.send_message(
                        query=last_message["content"],
                        chat_id=st.session_state.chat_id,
                        chat_history=st.session_state.chat_history[:-1]
                    )


                
                if result:
                    if result["response_type"] == "RAG_Prompt":
                        st.info("📚 Knowledge Base")
                    elif result["response_type"] == "Urgent_ticket":
                        st.success("🎫 Ticket Created")
                    elif result["response_type"] == "Confused_Query":
                        st.warning("❓ Help Request")
                    elif result["response_type"] == "Ticket_Status":
                        st.error("Ticket_Status")
                    
                    st.write(result["response"])
                    st.caption(f"⚡ Processed in {result['processing_time']:.2f}s")
                
                    assistant_message = {
                        "role": "assistant",
                        "content": result["response"],
                        "timestamp": datetime.now().strftime('%H:%M:%S'),
                        "type": result["response_type"],
                        "processing_time": result["processing_time"]
                    }
                    st.session_state.chat_history.append(assistant_message)
                    persist_history_now()
                    
                else:
                    st.error("Failed to get response from API")
                    error_message = {
                        "role": "assistant",
                        "content": "Sorry, I couldn't process your request. Please try again.",
                        "timestamp": datetime.now().strftime('%H:%M:%S'),
                        "type": "error"
                    }
                    st.session_state.chat_history.append(error_message)
            
            #Reset processing state after getting response
            st.session_state.is_processing = False
            if hasattr(st.session_state, 'processing_message_id'):
                delattr(st.session_state, 'processing_message_id')
            st.rerun()

if __name__ == "__main__":
    main()
