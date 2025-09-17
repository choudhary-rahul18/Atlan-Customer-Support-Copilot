import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np

# Page config
st.set_page_config(
    page_title="Tickets Dashboard",
    page_icon="🎫",
    layout="wide"
)



# Enhanced CSS matching your main theme
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
    .ticket-card {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #7c3aed;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-resolved {
        background-color: #fef3c7;
        color: #92400e;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .status-in-progress {
        background-color: #dbeafe;
        color: #1e40af;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .status-resolved {
        background-color: #d1fae5;
        color: #065f46;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .query-text {
        background: #e5e7eb;
        padding: 0.75rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        font-style: italic;
    }
    .response-text {
        background: #f0f9ff;
        padding: 0.75rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        border-left: 3px solid #0ea5e9;
    }
</style>
""", unsafe_allow_html=True)

# Load ticket data
@st.cache_data
def load_ticket_data():
    try:
        df = pd.read_excel('files/tickets.xlsx')
        # Convert time column to datetime if it's not already
        df['time'] = pd.to_datetime(df['time'])
        return df
    except FileNotFoundError:
        st.error("❌ tickets.xlsx file not found. Please make sure the file is in the same directory.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading tickets: {str(e)}")
        return pd.DataFrame()
    
def mark_resolved(ticket_id: str, ticket_path: str = "files/tickets.xlsx") -> bool:
    try:
        df = pd.read_excel(ticket_path)
        mask = df["ticket_id"] == ticket_id
        if not mask.any():
            return False
        df.loc[mask, "status"] = "Resolved"
        # Write back
        df.to_excel(ticket_path, index=False)
        # Invalidate only this function’s cache (preferred) or all data cache
        try:
            load_ticket_data.clear()  # clears cache for this function only
        except Exception:
            st.cache_data.clear()
        # Rerun so UI reflects the change immediately
        st.rerun()
        return True
    except Exception as e:
        st.error(f"Failed to update ticket: {e}")
        return False


# Header
st.markdown("""
<div class="main-header">
    <h2>Support Tickets Dashboard</h2>
    <p>Customer Support Ticket Management</p>
</div>
""", unsafe_allow_html=True)
st.cache_data.clear()
# Load data
df = load_ticket_data()


if df.empty:
    st.stop()


# Status filter - using actual status values from your Excel
status_options = ['All'] + sorted(df['status'].unique().tolist())
selected_status = st.sidebar.selectbox("Filter by Status", status_options)

# Search filter
search_term = st.sidebar.text_input("🔍 Search in tickets", placeholder="Search subject, query, or response...")

# Apply filters
filtered_df = df.copy()

if selected_status != 'All':
    filtered_df = filtered_df[filtered_df['status'] == selected_status]

if search_term:
    mask = (
        filtered_df['subject'].str.contains(search_term, case=False, na=False) |
        filtered_df['query'].str.contains(search_term, case=False, na=False) |
        filtered_df['response'].str.contains(search_term, case=False, na=False)
    )
    filtered_df = filtered_df[mask]

# Key metrics based on actual data
col1, col2, col3= st.columns(3)

with col1:
    total_tickets = len(filtered_df)
    st.metric("Total Tickets", total_tickets)

with col2:
    Resolved_tickets = len(filtered_df[filtered_df['status'] == 'Resolved'])
    st.metric("Resolved Tickets", Resolved_tickets)

with col3:
    in_progress_tickets = len(filtered_df[filtered_df['status'] == 'In Progress'])
    st.metric("In Progress", in_progress_tickets)

# with col4:
#     response_rate = len(filtered_df[filtered_df['response'].notna()]) / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
#     st.metric("Response Rate", f"{response_rate:.1f}%")

st.markdown("---")

# Function to get status badge HTML
def get_status_badge(status):
    if status == 'Resolved':
        return '<span class="status-Resolved">🟢 Resolved</span>'
    elif status == 'In Progress':
        return '<span class="status-in-progress">🔵 In Progress</span>'
    else:
        return f'<span class="status-in-progress">{status}</span>'

# Display tickets in dropdown format
st.markdown(f"### Tickets ({len(filtered_df)} found)")

if filtered_df.empty:
    st.info("No tickets found matching your filters.")
else:
    # Sort by time (newest first)
    filtered_df = filtered_df.sort_values('time', ascending=False)
    
    for index, row in filtered_df.iterrows():
        # Create expandable section for each ticket
        with st.expander(
            f"🎫 {row['ticket_id']} - {row['subject'][:60]}{'...' if len(str(row['subject'])) > 60 else ''}", 
            expanded=False
        ):
            # Ticket header with status and time
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Subject:** {row['subject']}")
                if pd.notna(row['chat_id']):
                    st.markdown(f"**Chat ID:** `{row['chat_id']}`")

                else:
                    st.markdown("**Chat ID:** *Not Available*")
                
            
            with col2:
                st.markdown(f"**Created:** {row['time'].strftime('%Y-%m-%d %H:%M')}")
                st.markdown(get_status_badge(row['status']), unsafe_allow_html=True)
            
            st.markdown("---")
            
            # User Query
            st.markdown("**🗣️ User Query:**")
            st.markdown(f'<div class="query-text">"{row["query"]}"</div>', unsafe_allow_html=True)
            
            # AI Response
            if pd.notna(row['response']) and str(row['response']).strip():
                st.markdown("**🤖 AI Response:**")
                st.markdown(f'<div class="response-text">{row["response"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown("**🤖 AI Response:**")
                st.info("*No response yet - Ticket pending*")
            
            # Action buttons
            (col1,) = st.columns(1)  # note the comma
            with col1:
                if st.button(f"✅ Mark Resolved", key=f"resolve_{row['ticket_id']}"):
                    ok = mark_resolved(row["ticket_id"])

            
            
                

# Sidebar statistics based on actual data
with st.sidebar:
    
    # Refresh button
    st.markdown("---")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #666; padding: 1rem;">
    Tickets Dashboard • Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")} IST<br>
    🤖 Atlan Customer Support Copilot
</div>
""", unsafe_allow_html=True)
