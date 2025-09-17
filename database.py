import pandas as pd
import logging
import os,json

ticket_directory = 'files/tickets.xlsx'
chat_history_directory = 'files/chat_history.xlsx'
# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create directory if it doesn't exist
def ensure_directory_exists(directory):
    """Ensure the directory exists, create if not"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"Created directory: {directory}")

# Function 1: Create a new ticket with auto-generated ID.         return-->updated_df, new_ticket_id
def create_ticket(df):
    """
    Creates a new ticket with auto-generated ID and default values
    
    Args:
        df: Existing DataFrame with tickets
    
    Returns:
        tuple: (updated_df, new_ticket_id)
    """
    # Generate new ticket ID
    if len(df) > 0:
        last_id = df['ticket_id'].iloc[-1]
        last_num = int(last_id.split('-')[1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    new_ticket_id = f"TICKET-{new_num:05d}"

    # Create ticket with default/empty values
    new_row = pd.DataFrame({
        'ticket_id': [new_ticket_id],
        'chat_id': [''],
        'subject': [''],
        'status': ['Open'],
        'query': [''],
        'response': [''],
        'time': [pd.Timestamp.now()]
    })
    
    updated_df = pd.concat([df, new_row], ignore_index=True)
    logging.info(f"Created new ticket: {new_ticket_id}")
    return updated_df, new_ticket_id

# Function 2: Fill/update details for an existing ticket     return--> Updated DataFrame
def fill_ticket_details(df, ticket_id, subject=None, query=None, response=None,chat_id=None, status= 'In Progress'):
    """
    Updates details for an existing ticket
    
    Args:
        df: DataFrame containing tickets
        ticket_id: ID of the ticket to update
        chat_id, subject, status, query, response: Optional fields to update
    
    Returns:
        DataFrame: Updated DataFrame
    """
    # Find the ticket by ID
    ticket_mask = df['ticket_id'] == ticket_id
    if not ticket_mask.any():
        logging.error(f"Ticket ID {ticket_id} not found")
        return df
    
    # Track what fields are being updated
    updated_fields = []
    
    # Update only provided fields
    if chat_id is not None:
        df.loc[ticket_mask, 'chat_id'] = chat_id
        updated_fields.append('chat_id')
    if subject is not None:
        df.loc[ticket_mask, 'subject'] = subject
        updated_fields.append('subject')
    if status is not None:
        df.loc[ticket_mask, 'status'] = 'In Progress'
        updated_fields.append('status')
    if query is not None:
        df.loc[ticket_mask, 'query'] = query
        updated_fields.append('query')
    if response is not None:
        df.loc[ticket_mask, 'response'] = response
        updated_fields.append('response')
    if updated_fields:
        logging.info(f"Updated ticket {ticket_id} - fields: {', '.join(updated_fields)}")
    else:
        logging.warning(f"No fields provided to update for ticket {ticket_id}")
    
    return df

# Safe save function with logging
def save_tickets_to_file(df, filename=ticket_directory):
    """
    Safely save DataFrame to Excel with proper error handling and logging
    """
    try:
        ensure_directory_exists(os.path.dirname(filename))
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        logging.info(f"Successfully saved {len(df)} tickets to {filename}")
        return True
        
    except PermissionError:
        logging.error(f"Permission denied: {filename} may be open in another program")
        return False
    except Exception as e:
        logging.error(f"Failed to save file {filename}: {str(e)}")
        return False


def check_existing_ticket_by_chat_id(chat_id):
    df = pd.read_excel(ticket_directory)
    if chat_id is None or chat_id == "":
        logging.warning("Empty or None chat_id provided to check_existing_ticket_by_chat_id")
        output = {
            "already_ticket":"no",
            "remarks":"No ticket_id is found in the database."
        }
        return output
    
    # Filter tickets by chat_id (excluding empty chat_ids)
    matching_ticket = df[df['chat_id'] == chat_id]
    
    if not matching_ticket.empty:
        ticket_id = matching_ticket.iloc[0]['ticket_id']
        subject = matching_ticket.iloc[0]['subject'] 
        timestamp = matching_ticket.iloc[0]['time']

        output = {
            "already_ticket":"yes",
            "remarks":f"Found existing ticket for chat_id {chat_id}: {ticket_id} with subject: <{subject}> at time: <{timestamp}>"
        }
        
        logging.info(f"Found existing ticket for chat_id {chat_id}: {ticket_id}")
        return output
    else:

        output = {
            "already_ticket": "no",
            "remarks": f"No existing ticket found for chat_id {chat_id}"
        }
        logging.info(f"No existing ticket found for chat_id {chat_id}")
        return output

def get_ticket_details_by_chat_id(chat_id, ticket_id=None,ticket_directory=ticket_directory):
    """
    Fetch ticket details (ticket_id, status, timestamp) for a given chat_id.
    
    Returns:
        dict with keys:
            - message: str (human-readable summary)
    """

    try:
        df = pd.read_excel(ticket_directory)

        if not chat_id:
            logging.warning("Empty chat_id provided to get_ticket_details_by_chat_id")
            return {
                "message": "No Chat Id provided.Please re enter Chat ID and Ticket ID, for example 'Chat ID is 12345678 and Ticket ID is 00001'"
            }

        if ticket_id==None:
            matching_ticket = df[(df['chat_id'] == chat_id)]
        else:
            matching_ticket = df[(df['chat_id'] == chat_id) & (df['ticket_id'] == ticket_id)]

        if not matching_ticket.empty:
            ticket_id = matching_ticket.iloc[0]['ticket_id']
            status = matching_ticket.iloc[0]['status']
            timestamp = matching_ticket.iloc[0]['time']

            logging.info(f"Ticket found for chat_id {chat_id}: {ticket_id}, Status={status}, Time={timestamp}")
            if status.lower() == "resolved":
                return {
                    "message": (
                        f"Your ticket **{ticket_id}** has already been *resolved*. "
                        f"It was created on {timestamp}, and our team has marked it as successfully closed. "
                        f"If everything looks good on your side, no further action is needed. "
                        f"But if you still face any issues, feel free to reopen the ticket or raise a new one — we’ll be happy to help! 😊"
                    )
                }
            elif status.lower() == "in progress":
                return {
                    "message": (
                        f"Your ticket **{ticket_id}** is currently *in progress*. "
                        f"Our support team is actively working on it since {timestamp}. "
                        f"We’ll keep you updated as soon as there’s any progress or resolution. "
                        f"Thanks for your patience — we truly appreciate it!"
                    )
                }


        else:
            logging.info(f"Your Chat ID {chat_id} and Ticket ID {ticket_id} doesn't match. Kindly check carefully and try again :)")
            return {
                "message": f"Your Chat ID {chat_id} and Ticket ID {ticket_id} doesn't match. Kindly check carefully and try again :)"
            }

    except Exception as e:
        logging.error(f"Error while fetching ticket details: {e}")
        return {
            "message": f"Error occurred: {str(e)}"
        }


def delete_ticket_by_id(df, ticket_id):
    # Get count before deletion for logging
    original_count = len(df)
    
    # Perform deletion - keep all rows except the one with matching ticket_id
    df[df['ticket_id'] != ticket_id].reset_index(drop=True)
    
    logging.info(f"Successfully deleted ticket {ticket_id}. Tickets: {original_count}")
    return


def persist_chat_history(chat_id: str, chat_history: list, path: str = chat_history_directory) -> bool:
    """
    Upsert chat history by Chat ID:
      - If Chat ID exists -> update its 'Chat History' cell (overwrite).
      - Else -> append a new row.
    File is created with headers if missing.
    """
    try:
        # Row payload (store history as JSON string)
        row = {
            "Chat ID": chat_id,
            "Chat History": json.dumps(chat_history, ensure_ascii=False),
        }

        if os.path.exists(path):
            df = pd.read_excel(path)

            # Ensure required columns exist
            expected_cols = ["Chat ID", "Chat History"]
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = None

            # Normalize column order
            df = df[expected_cols]

            # Check if Chat ID already exists
            mask = df["Chat ID"].astype(str) == str(chat_id)
            if mask.any():
                # Overwrite the existing row's history
                df.loc[mask, "Chat History"] = row["Chat History"]
            else:
                # Append new row
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        else:
            # Create new file with headers and first row
            df = pd.DataFrame([row], columns=["Chat ID", "Chat History"])

        # Persist to disk
        df.to_excel(path, index=False)
        return True

    except Exception as e:
        print(f"[persist_chat_history] Error: {e}")
        return False

