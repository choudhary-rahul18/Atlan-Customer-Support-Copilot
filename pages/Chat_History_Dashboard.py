import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="Chat History", page_icon="💬", layout="wide")

# Theme CSS
st.markdown("""
<style>
  .main-header {
    text-align: center; padding: 1rem;
    background: linear-gradient(135deg,#1e3a8a,#7c3aed,#a855f7);
    color: white; border-radius: 10px; margin-bottom: 1rem;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  }
  .json-box {
    background: #f8fafc; padding: 0.75rem; border-radius: 8px;
    border-left: 4px solid #7c3aed;
  }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
  <h2>Chat History Dashboard</h2>
  <p>Per-chat transcripts with searchable, expandable details</p>
</div>
""", unsafe_allow_html=True)

CHAT_HISTORY_PATH = "files/chat_history.xlsx"

@st.cache_data
def load_chat_history(path: str):
    try:
        df = pd.read_excel(path)
        # Normalize required columns
        for col in ["Chat ID", "Chat History"]:
            if col not in df.columns:
                df[col] = None
        
        # Parse JSON safely
        def parse_json(s):
            try:
                if pd.isna(s): 
                    return []
                if isinstance(s, list):
                    return s
                return json.loads(str(s))
            except Exception:
                return []
        
        df["parsed_history"] = df["Chat History"].apply(parse_json)
        df["turns"] = df["parsed_history"].apply(lambda x: len(x) if isinstance(x, list) else 0)
        df["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return df
    except Exception as e:
        st.error(f"Error loading chat history: {e}")
        return pd.DataFrame()

# Always reload fresh on navigation
st.cache_data.clear()

try:
    df = load_chat_history(CHAT_HISTORY_PATH)
    if df.empty:
        st.info("No chat history found or file is empty.")
        st.stop()
except FileNotFoundError:
    st.error("❌ chat_history.xlsx not found in files/ directory.")
    st.stop()
except Exception as e:
    st.error(f"❌ Failed to load chat history: {e}")
    st.stop()


# Search filter
search = st.sidebar.text_input("🔍 Search Chat ID or message content", placeholder="Type to search...")



# Apply filters
filtered = df.copy()


# Text search in Chat ID or message content
if search:
    search_lower = search.lower()
    
    def match_row(row):
        # Search in Chat ID
        if search_lower in str(row["Chat ID"]).lower():
            return True
        
        # Search in message content
        msgs = row["parsed_history"] or []
        for msg in msgs:
            if isinstance(msg, dict):
                content = str(msg.get("content", "")).lower()
                if search_lower in content:
                    return True
        return False
    
    filtered = filtered[filtered.apply(match_row, axis=1)]

# KPI Metrics
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Chats", len(filtered))

with col2:
    median_turns = int(filtered["turns"].median()) if len(filtered) > 0 else 0
    st.metric("Median Turns", median_turns)

with col3:
    max_turns = int(filtered["turns"].max()) if len(filtered) > 0 else 0
    st.metric("Max Turns", max_turns)

st.markdown("---")

# Display chat history
st.markdown(f"### Chat History ({len(filtered)} found)")

if filtered.empty:
    st.info("No chats match the current filters.")
else:
    filtered_sorted = filtered.iloc[::-1]
    
    for idx, row in filtered_sorted.iterrows():
        chat_id = str(row["Chat ID"])
        turns = row["turns"]
        
        # Create header for expander
        if turns == 0:
            header = f"💬 {chat_id} • Empty chat"
        else:
            header = f"💬 {chat_id} • {turns} turn{'s' if turns != 1 else ''}"
        
        with st.expander(header, expanded=False):
            # Chat metadata
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Chat ID:** `{chat_id}`")
                st.markdown(f"**Total Turns:** {turns}")
            
            with col2:
                st.markdown(f"**Last Updated:** {row['last_updated']}")
            
            st.markdown("---")
            
            # Display chat transcript
            if turns == 0:
                st.info("No messages in this chat yet.")
            else:
                st.markdown("**Chat Transcript:**")
                
                # Option 1: Pretty JSON view (collapsible)
                with st.expander("View as JSON", expanded=False):
                    st.json(row["parsed_history"])
                
                # Option 2: Readable message format (default)
                messages = row["parsed_history"] or []
                for i, msg in enumerate(messages, 1):
                    if isinstance(msg, dict):
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")
                        timestamp = msg.get("timestamp", "")
                        msg_type = msg.get("type", "")
                        
                        # Role styling
                        if role == "user":
                            role_emoji = "🗣️"
                            role_style = "**User**"
                        elif role == "assistant":
                            role_emoji = "🤖"
                            role_style = "**Assistant**"
                        else:
                            role_emoji = "💬"
                            role_style = f"**{role.title()}**"
                        
                        # Message header
                        header_parts = [f"{role_emoji} {role_style}"]
                        if timestamp:
                            header_parts.append(f"*{timestamp}*")
                        if msg_type:
                            header_parts.append(f"`{msg_type}`")
                        
                        st.markdown(" • ".join(header_parts))
                        
                        # Message content
                        st.markdown(f"> {content}")
                        
                        if i < len(messages):
                            st.markdown("")
            
            st.markdown("---")
            
            # Action buttons
            col1, = st.columns(1)
            
            with col1:
                if turns > 0:
                    if st.button(" Export JSON", key=f"export_{chat_id}"):
                        json_data = json.dumps(row["parsed_history"], ensure_ascii=False, indent=2)
                        st.download_button(
                            label="Download JSON",
                            data=json_data,
                            file_name=f"chat_{chat_id}.json",
                            mime="application/json",
                            key=f"dl_{chat_id}"
                        )
                else:
                    st.write("*No data to export*")
            
# Sidebar refresh button
with st.sidebar:
    st.markdown("---")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #666; padding: 1rem;">
     Chat History Dashboard • Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")} IST<br>
    🤖 Atlan Customer Support Copilot
</div>
""", unsafe_allow_html=True)
