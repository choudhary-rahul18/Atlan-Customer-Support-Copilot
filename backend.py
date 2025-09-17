# backend.py - Complete API Backend Service
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.globals import set_verbose, set_debug
from pydantic import BaseModel
import pandas as pd
from typing import Optional, Dict, Any, List
import uvicorn
import logging
import time
import json
from datetime import datetime
import random

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from rag import ExcelRAG, retrieve_data_function, referal_links
from prompts import master_prompt, Urgent_ticket, RAG_Prompt, Confused_Query, Ticket_Status
from database import (ensure_directory_exists, create_ticket, fill_ticket_details,
                     save_tickets_to_file, check_existing_ticket_by_chat_id, delete_ticket_by_id, persist_chat_history)

import importlib,sys
# Force reload database module if already imported
if 'database' in sys.modules:
    importlib.reload(sys.modules['database'])

from database import get_ticket_details_by_chat_id
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Customer Support API",
    description="Complete FastAPI backend for AI-powered customer support system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Welcome Message
welcome_text = ["Welcome! I'm here to provide you with fast, accurate support 24/7. Whether you need technical help, account assistance, or general information, I've got you covered.",
                "Hello! I'm your dedicated support assistant, designed to help you get the most out of our services. What would you like assistance with today?",
                "Hello! Welcome to our support center. I'm here to assist you with any questions or concerns you might have. How can I make your day better?",
                "Hi there! I'm your AI support assistant, here to help you find answers quickly and easily. What can I help you with today?",
                  "Hey! Thanks for reaching out. I'm your friendly support companion, ready to help you solve problems and find the information you need.",
                  "Hi! I'm here to help you get answers fast. Ask me about technical issues, account questions, or anything else you need support with."]



# Configuration
TICKET_DIRECTORY = 'files/tickets.xlsx'
TAGS = [
    "API", "SDK", "SSO", "CLI", "Atlan Client", "Developer Portal", "Batch Operations",
    "Custom Metadata", "Business Metadata", "Certificate", "Data Governance", "Announcement",
    "Data Lineage", "OpenLineage", "Authentication & Security", "API Key", "Access Control",
    "Build Tools", "Deployment", "Webhooks", "Audit Log", "Search Log", "Suggestions",
    "Fluent Search", "Data Sources", "Integration", "AWS Lambda", "Code Examples", "Configuration"
]


# Pydantic Models
class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None
    type: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    chat_id: str
    chat_history: List[Message] = []

class TicketInfo(BaseModel):
    ticket_id: str
    subject: str
    status: str
    priority: str

class QueryResponse(BaseModel):
    response: str
    response_type: str
    sentiment: Optional[str]
    ticket_info: Optional[TicketInfo]
    processing_time: float
    timestamp: str

class SystemStatus(BaseModel):
    llm: bool
    rag: bool
    database: bool
    overall: bool
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime: float

# Global backend state
class BackendState:
    def __init__(self):
        self.llm = None
        self.rag = None
        self.rag_initialized = False
        self.llm_initialized = False
        self.start_time = time.time()
        
        # Initialize on startup
        self._initialize_systems()
    
    def _initialize_systems(self):
        """Initialize all backend systems"""
        logger.info("   ::::>>> Initializing AI Customer Support Backend...")
        
        # Initialize LLM
        self._initialize_llm()
        
        # Initialize RAG
        self._initialize_rag()
        
        logger.info("   ::::>>> Backend initialization complete!")
    
    def _initialize_llm(self):
        """Initialize LLM system"""
        try:
            load_dotenv()
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo", 
                temperature=0.5
            )
            self.llm_initialized = True
            logger.info("   ::::>>> LLM initialized successfully")
        except Exception as e:
            logger.error(f"   ::::>>> LLM initialization failed: {str(e)}")
            self.llm_initialized = False
    
    def _initialize_rag(self):
        """Initialize RAG system"""
        try:
            logging.basicConfig(level=logging.INFO)
            self.rag = ExcelRAG(chunk_file="files/chunks.json")
            dataframe = self.rag.load_excel("files/sample1.xlsx")
            chunks = self.rag.load_chunks()
            self.rag.create_embeddings()
            self.rag.build_bm25_index()
            self.rag_initialized = True
            logger.info("   ::::>>> RAG system initialized successfully")
        except Exception as e:
            logger.error(f"   ::::>>> RAG initialization failed: {str(e)}")
            self.rag_initialized = False
    
    def get_llm(self):
        """Get LLM instance"""
        if not self.llm_initialized:
            self._initialize_llm()
        return self.llm
    
    def run_llm_task(self, prompt_template, debug_mode=False, **kwargs):
        """Execute LLM task with optional reasoning visibility"""
        try:
            if debug_mode:
                set_verbose(True)
                set_debug(True)
            
            model = self.get_llm()
            if not model:
                return None
            
            chain = prompt_template | model
            result = chain.invoke(kwargs)
            
            # Log the reasoning process for master agent decisions
            if debug_mode and 'master_agent' in str(prompt_template):
                logger.info(f"   ::::>>>  Master Agent Reasoning: {result.content}")
            
            return result.content.strip()
        except Exception as e:
            logger.error(f"LLM task error: {str(e)}")
            return None
        finally:
            if debug_mode:
                set_verbose(False)
                set_debug(False)
    
    def master_agent(self, query,current_chat_id, chat_history, tags=TAGS):
        """Your exact master agent function"""
        return self.run_llm_task(
            prompt_template=master_prompt,
            query=query,
            tags=tags,
            chat_history=chat_history,
            chat_id = current_chat_id
        )
    
    def urgent_ticket_bot(self, query, sentiment, chat_history, chat_id, remarks, ticket_id):
        """Your exact urgent ticket bot function"""
        return self.run_llm_task(
            prompt_template=Confused_Query,
            query=query,
            sentiment=sentiment,
            ticket_id=ticket_id,
            chat_history=chat_history,
            remarks=remarks,
            chat_id=chat_id
        )
    #ticket_id, chat_id, chat_history, remarks, sentiment,query
    def ticket_status_bot(self, query, chat_history):   #chat_history,query
        return self.run_llm_task(
            prompt_template= Ticket_Status,
            query=query,
            chat_history=chat_history
        )


    def unresolved_query_bot(self, chat_id, remarks, sentiment, ticket_id, chat_history, query):
        """Your exact unresolved query bot function"""
        return self.run_llm_task(
            prompt_template=Urgent_ticket,
            query=query,
            sentiment=sentiment,
            ticket_id=ticket_id,
            chat_history=chat_history,
            remarks=remarks,
            chat_id=chat_id
        )
    
    def chatbot(self, query, context, chat_history):
        """Your exact chatbot function"""
        return self.run_llm_task(
            prompt_template=RAG_Prompt,
            context=context,
            query=query,
            chat_history=chat_history
        )
    
    def give_ticket_status(self, query, condition, chat_history, present_chat_id):
        logger.info(f"Prompt Condition: {condition}")
        try:
            exist_ticket = check_existing_ticket_by_chat_id(present_chat_id)
            if condition == "Present":
                if exist_ticket["already_ticket"] == "yes":
                    response = get_ticket_details_by_chat_id(present_chat_id, ticket_id=None)
                    if isinstance(response, dict):
                        return response["message"]
                    else:
                        # If for some reason it's a string, then parse it
                        try:
                            response_data = json.loads(response)
                            return response_data["message"]
                        except json.JSONDecodeError:
                            return "Error parsing ticket details."
                
                elif exist_ticket["already_ticket"] == "no":
                    ticket_response = self.ticket_status_bot(query, chat_history)
                    logger.info(f"Raw LLM response: {ticket_response}")
                    
                    try:
                        ticket = json.loads(ticket_response.strip())
                        
                        # POST-PROCESSING VALIDATION
                        chat_id = str(ticket.get("chat_id", "")).strip()
                        ticket_id = str(ticket.get("ticket_id", "")).strip()
                        
                        logger.debug(f"Extracted - Chat ID: '{chat_id}', Ticket ID: '{ticket_id}'")
                        
                        # Override LLM decision with correct logic
                        if chat_id and ticket_id and chat_id != "" and ticket_id != "":
                            if ticket.get("subject") == "Not Complete":
                                logger.warning("🔧 LLM Error Detected: Both IDs found but marked incomplete. Fixing...")
                                ticket["subject"] = "Complete"
                        elif not chat_id or not ticket_id or chat_id == "" or ticket_id == "":
                            if ticket.get("subject") == "Complete":
                                logger.warning("🔧 LLM Error Detected: Missing IDs but marked complete. Fixing...")
                                ticket["subject"] = "Not Complete"
                        
                        logger.info(f"Final decision: {ticket.get('subject')}")
                        
                        if ticket["subject"] == "Complete":
                            response = get_ticket_details_by_chat_id(chat_id, ticket_id)
                            if isinstance(response, dict):
                                return response["message"]
                            else:
                                try:
                                    response_data = json.loads(response)
                                    return response_data["message"]
                                except json.JSONDecodeError:
                                    return "Error retrieving ticket details."
                                    
                        elif ticket["subject"] == "Not Complete":
                            return ticket.get("response", "Missing information. Please provide both Chat ID and Ticket ID.")
                            
                    except json.JSONDecodeError:
                        return "Error parsing ticket status response. Please try again."
            elif condition == "Past":
                    ticket_response = self.ticket_status_bot(query, chat_history)
                    logger.info(f"Raw LLM response: {ticket_response}")
                    
                    try:
                        ticket = json.loads(ticket_response.strip())
                        chat_id = str(ticket.get("chat_id", "")).strip()
                        ticket_id = str(ticket.get("ticket_id", "")).strip()
                        
                        logger.debug(f"Extracted - Chat ID: '{chat_id}', Ticket ID: '{ticket_id}'")
                        
                        # Override LLM decision with correct logic
                        if chat_id and ticket_id and chat_id != "" and ticket_id != "":
                            if ticket.get("subject") == "Not Complete":
                                logger.warning("🔧 LLM Error Detected: Both IDs found but marked incomplete. Fixing...")
                                ticket["subject"] = "Complete"
                        elif not chat_id or not ticket_id or chat_id == "" or ticket_id == "":
                            if ticket.get("subject") == "Complete":
                                logger.warning("🔧 LLM Error Detected: Missing IDs but marked complete. Fixing...")
                                ticket["subject"] = "Not Complete"
                        
                        logger.info(f"Final decision: {ticket.get('subject')}")
                        
                        # Add the missing logic after validation
                        if ticket["subject"] == "Complete":
                            response = get_ticket_details_by_chat_id(chat_id, ticket_id)
                            if isinstance(response, dict):
                                return response["message"]
                            else:
                                try:
                                    response_data = json.loads(response)
                                    return response_data["message"]
                                except json.JSONDecodeError:
                                    return "Error retrieving ticket details."
                                    
                        elif ticket["subject"] == "Not Complete":
                            return ticket.get("response", "Missing information. Please provide both Chat ID and Ticket ID.")
                            
                    except json.JSONDecodeError:
                        return "Error parsing ticket status response. Please try again."

        
        except Exception as e:
            logger.error(f"Error in give_ticket_status: {e}")
            return "An error occurred while checking ticket status. Please try again."

                        



    def create_ticket_and_update(self, directory, sentiment, query, chat_history, exist_ticket, chat_id):
        """Your exact ticket creation function"""
        try:
            ensure_directory_exists(directory)
            df = pd.read_excel(directory)
            updated_df, ticket = create_ticket(df)
            ticket_existance = exist_ticket
            
            if ticket_existance["already_ticket"] == "no":
                result = self.urgent_ticket_bot(query, sentiment, chat_history, chat_id, 
                                               remarks=ticket_existance["remarks"], ticket_id=ticket)
                if result:
                    result_dict = json.loads(result)
                    subject = result_dict["subject"]
                    response = result_dict["response"]
                    df = fill_ticket_details(updated_df, ticket, subject, query, response, chat_id)
                    save_tickets_to_file(df)
                    
                    ticket_info = TicketInfo(
                        ticket_id=str(ticket),
                        subject=subject,
                        status="Created",
                        priority="High" if "urgent" in query.lower() else "Normal"
                    )
                    return response, ticket_info
                
            elif ticket_existance["already_ticket"] == "yes":
                delete_ticket_by_id(df, ticket_id=ticket)
                logger.info(ticket_existance["remarks"])
                ticket = None
                result = self.urgent_ticket_bot(query, sentiment, chat_history, chat_id, 
                                               remarks=ticket_existance["remarks"], ticket_id=ticket)
                if result:
                    result_dict = json.loads(result)
                    response = result_dict["response"]
                    return response, None
        except Exception as e:
            logger.error(f"Ticket creation error: {str(e)}")
            return f"Error creating ticket: {str(e)}", None
    
    def create_ticket_confused_query(self, directory, chat_id, sentiment, chat_history, query, exist_ticket):
        """Your exact confused query function"""
        try:
            ensure_directory_exists(directory)
            df = pd.read_excel(directory)
            updated_df, ticket = create_ticket(df)
            ticket_existance = exist_ticket
            
            if ticket_existance["already_ticket"] == "no":
                result = self.unresolved_query_bot(chat_id, ticket_existance, sentiment, ticket, chat_history, query)
                if result:
                    result_dict = json.loads(result)
                    subject = result_dict["subject"]
                    response = result_dict["response"]
                    df = fill_ticket_details(updated_df, ticket, subject, query, response, chat_id)
                    save_tickets_to_file(df)
                    
                    ticket_info = TicketInfo(
                        ticket_id=str(ticket),
                        subject=subject,
                        status="Created",
                        priority="Normal"
                    )
                    return response, ticket_info
                
            elif ticket_existance["already_ticket"] == "yes":
                delete_ticket_by_id(df, ticket_id=ticket)
                logger.info(ticket_existance["remarks"])
                ticket = None
                result = self.unresolved_query_bot(chat_id, ticket_existance, sentiment, ticket, chat_history, query)
                if result:
                    result_dict = json.loads(result)
                    response = result_dict["response"]
                    return response, None
        except Exception as e:
            logger.error(f"Confused query error: {str(e)}")
            return f"Error processing help request: {str(e)}", None
    
    def get_system_status(self):
        """Get system status"""
        try:
            db_status = True
            try:
                ensure_directory_exists(TICKET_DIRECTORY)
            except:
                db_status = False
            
            return SystemStatus(
                llm=self.llm_initialized,
                rag=self.rag_initialized,
                database=db_status,
                overall=self.llm_initialized and self.rag_initialized and db_status,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"System status error: {str(e)}")
            return SystemStatus(
                llm=False,
                rag=False,
                database=False,
                overall=False,
                timestamp=datetime.now().isoformat()
            )
    
    def process_query(self, query: str, chat_id: str, chat_history: List[Message]):
        """Main query processing - Your exact logic"""
        start_time = time.time()
        
        try:
            # Format chat history exactly like CLI version
            formatted_chat_history = ""
            if len(chat_history) > 1:
                recent_messages = chat_history[-5:-1] if len(chat_history) > 1 else []
                for msg in recent_messages:
                    role = "User" if msg.role == "user" else "Assistant"
                    formatted_chat_history += f"{role}: {msg.content}\n"

            # Format chat history with only user inputs
            user_chat_history = ""
            if len(chat_history) > 1:
                recent_messages = chat_history[-5:-1] if len(chat_history) > 1 else []
                for msg in recent_messages:
                    if msg.role == "user":  # Only include user messages
                        user_chat_history += f"User: {msg.content}\n"

            try:
                planning_response = self.master_agent(query,chat_id,formatted_chat_history)
                logger.info(f"Planning response from Master Agent: {planning_response}")
                if not planning_response:
                    raise Exception("No response from master agent")
                planning = json.loads(planning_response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                processing_time = time.time() - start_time
                return QueryResponse(
                    response="Error parsing planning response. Please try again.",
                    response_type="error",
                    sentiment=None,
                    ticket_info=None,
                    processing_time=processing_time,
                    timestamp=datetime.now().isoformat()
                )
            except Exception as e:
                logger.error(f"Master agent error: {str(e)}")
                processing_time = time.time() - start_time
                return QueryResponse(
                    response=f"Error with master agent: {e}",
                    response_type="error",
                    sentiment=None,
                    ticket_info=None,
                    processing_time=processing_time,
                    timestamp=datetime.now().isoformat()
                )
            logger.info(f'Prompt Type: {planning["prompt_type"]}')
            if planning["prompt_type"] == "RAG_Prompt":
                retrieved_context, full_detail = retrieve_data_function(query)
                links = referal_links(full_detail)
                response = self.chatbot(query, retrieved_context, formatted_chat_history)
                if response:
                    response = response + "\n" + links
                else:
                    response = "I couldn't retrieve the requested information. Please try rephrasing your question."
                
                processing_time = time.time() - start_time
                return QueryResponse(
                    response=response,
                    response_type=planning["prompt_type"],
                    sentiment=planning.get("sentiment", "Neutral"),
                    ticket_info=None,
                    processing_time=processing_time,
                    timestamp=datetime.now().isoformat()
                )
                
            elif planning["prompt_type"] == "Urgent_ticket":
                sentiment = planning["sentiment"]
                exist_ticket = check_existing_ticket_by_chat_id(chat_id)
                response, ticket_info = self.create_ticket_and_update(
                    TICKET_DIRECTORY, sentiment, query, formatted_chat_history, exist_ticket, chat_id
                )
                
                processing_time = time.time() - start_time
                return QueryResponse(
                    response=response,
                    response_type=planning["prompt_type"],
                    sentiment=sentiment,
                    ticket_info=ticket_info,
                    processing_time=processing_time,
                    timestamp=datetime.now().isoformat()
                )

            elif planning["prompt_type"] == "Confused_Query":
                sentiment = planning["sentiment"]
                exist_ticket = check_existing_ticket_by_chat_id(chat_id)
                response, ticket_info = self.create_ticket_confused_query(
                    TICKET_DIRECTORY, chat_id, sentiment, formatted_chat_history, query, exist_ticket
                )
                
                processing_time = time.time() - start_time
                return QueryResponse(
                    response=response,
                    response_type=planning["prompt_type"],
                    sentiment=sentiment,
                    ticket_info=ticket_info,
                    processing_time=processing_time,
                    timestamp=datetime.now().isoformat()
                )
            elif planning["prompt_type"] == "Ticket_Status":
                condition = planning["condition"]
                response = self.give_ticket_status(query,condition, user_chat_history, chat_id)
                
                processing_time = time.time() - start_time
                return QueryResponse(
                    response=response,
                    response_type=planning["prompt_type"],
                    sentiment=planning.get("sentiment", "Neutral"),
                    ticket_info=None,  # Ticket status queries don't create new tickets
                    processing_time=processing_time,
                    timestamp=datetime.now().isoformat())

            elif planning["prompt_type"] == "Acknowledgment":
                processing_time = time.time() - start_time
                return QueryResponse(
                    response="You're welcome! Feel free to reach out if you need any further assistance. Have a great day! 😊",
                    response_type="Acknowledgment", 
                    sentiment=planning.get("sentiment", "Satisfied"),
                    ticket_info=None,
                    processing_time=processing_time,
                    timestamp=datetime.now().isoformat()
                )



            else:
                processing_time = time.time() - start_time
                return QueryResponse(
                    response=f"Unhandled prompt type: {planning['prompt_type']}",
                    response_type="error",
                    sentiment=None,
                    ticket_info=None,
                    processing_time=processing_time,
                    timestamp=datetime.now().isoformat()
                )
                
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            processing_time = time.time() - start_time
            return QueryResponse(
                response=f"Could you please share a bit more detail about your query?",
                response_type="error",
                sentiment=None,
                ticket_info=None,
                processing_time=processing_time,
                timestamp=datetime.now().isoformat()
            )

# Initialize backend state
backend_state = BackendState()

# API Endpoints
@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Customer Support API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
        "status": "/status"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    uptime = time.time() - backend_state.start_time
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        uptime=uptime
    )

@app.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get detailed system status"""
    return backend_state.get_system_status()

@app.get("/welcome")
async def welcome_message():
    return {"message": random.choice(welcome_text)}

@app.post("/query", response_model=QueryResponse)
async def process_query_endpoint(request: QueryRequest):
    """Process user query - Main endpoint"""
    try:
        logger.info(f"Processing query for chat_id: {request.chat_id}")
        result = backend_state.process_query(
            query=request.query,
            chat_id=request.chat_id,
            chat_history=request.chat_history
        )
        logger.info(f"Query processed in {result.processing_time:.2f}s")
        return result
    except Exception as e:
        logger.error(f"Endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tickets/{chat_id}")
async def get_tickets_by_chat_id(chat_id: str):
    """Get tickets for a specific chat ID"""
    try:
        exist_ticket = check_existing_ticket_by_chat_id(chat_id)
        return {"chat_id": chat_id, "ticket_info": exist_ticket}
    except Exception as e:
        logger.error(f"Ticket lookup error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Startup event"""
    logger.info(" ::::>>> FastAPI Customer Support Backend is starting up....")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    logger.info("👋 FastAPI Customer Support Backend is shutting down...")


class PersistRequest(BaseModel):
    chat_id: str
    chat_history: list

@app.post("/sessions/persist")
async def persist_session(req: PersistRequest):
    try:
        ok = persist_chat_history(req.chat_id, req.chat_history)
        if not ok:
            raise HTTPException(status_code=500, detail="Persist failed")
        return {"ok": True, "saved": True, "chat_id": req.chat_id}
    except Exception as e:
        logger.error(f"Persist error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
