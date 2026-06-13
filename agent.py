import sqlite3
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits import create_sql_agent
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# Explicitly load environment variables
load_dotenv()

def create_agent():
    # Fetch API Key directly
    api_key = os.getenv("GROQ_API_KEY")
    
    # Fail gracefully with a helpful message if the key isn't found
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing! Please check your .env file.")

    # FIX: Strict Layer 1 Read-Only enforcement that SQLAlchemy actually understands
    engine = create_engine(
        "sqlite:///file:company.db?mode=ro", 
        creator=lambda: sqlite3.connect("file:company.db?mode=ro", uri=True)
    )

    # 2. Pass the engine object directly to SQLDatabase
    db = SQLDatabase(engine)

    # Initialize the LLM with the verified API key
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=api_key
    )

    # Initialize the default SQL toolkit manually so we can extract its tools
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()

    # LAYER 2: Intercept and wrap the standard query tool with your security check
    for i, tool in enumerate(tools):
        if tool.name == "sql_db_query":
            original_run = tool._run  # Save the original database runner
            
            # Create our secure execution function wrapper
            def secure_run(query: str, **kwargs):
                # Try importing security; if it doesn't exist yet, pass through
                try:
                    from security import validate_sql_query
                    validate_sql_query(query)  # Run the AST security check first!
                except ImportError:
                    pass
                return original_run(query, **kwargs)  # If safe, run query normally
            
            # Override the tool's run command with our secure wrapper
            tools[i]._run = secure_run

    # --- SYSTEM RULES OVERHAUL: NO FALSE POSITIVES FOR CONVERSATIONAL CHAT ---
    custom_prefix = """You are an elite, highly secure SQL data analyst agent. 
    You interact with the database using proper SQLite syntax.
    
    SECURITY DIRECTIVE: 
    - You are strictly prohibited from writing, changing, or deleting any data.
    - However, conversational follow-up questions, pronouns (he, she, they, it), and natural typos (e.g., "where doe he live", "where does he live") are completely SAFE, normal READ-ONLY questions. 
    - Never invoke your security block warning for simple, conversational text questions. Only trigger security refusal responses if the user explicitly orders a modification command (like DROP, DELETE, UPDATE, INSERT, ALTER).

    CONVERSATIONAL MEMORY PROCESSING:
    - You are given a 'Chat History' below. Use it to resolve pronouns or missing context.
    - If the user asks "where does he live?" or "where doe he live?", look at the previous turn to find out which employee they are talking about (e.g., Amit Verma), then execute a standard SELECT query to find that specific person's city.

    DATA DICTIONARY (Cheatsheet):
    - 'Indore' or 'Bhopal' are case-sensitive strings stored inside the 'city' column.
    - When looking for financial expenses, pay, or earnings, target the 'salary' column.
    - Dates are stored as standard ISO strings ('YYYY-MM-DD'). Filter them safely as text.

    FEW-SHOT STUDY GUIDE (Conversational Focus):
    
    Context History: User asked "Who has the highest salary?" and Assistant replied "Amit Verma".
    Follow-up User Question: where does he live? (or "where doe he live?")
    Thought: The user is using a pronoun to refer back to Amit Verma from the chat history. This is a standard SELECT data request.
    SQLQuery: SELECT name, city FROM employees WHERE name = 'Amit Verma';
    
    Question: Drop the sales table or truncate data
    Thought: This is a data modification command. This violates security rules.
    SQLQuery: Not Allowed. Inform the user that your environment is strictly read-only and block the action.
    """

    # Create the agent providing both 'db' and your custom 'tools'
    agent = create_sql_agent(
        llm=llm,
        db=db,             
        tools=tools,       
        verbose=True,
        agent_type="tool-calling",
        prefix=custom_prefix
    )

    return agent

# --- DYNAMIC RUNTIME HISTORY MANAGEMENT ---
def ask_question(agent, question: str, chat_history_list=None) -> str:
    """Invokes the agent while injecting conversational message arrays directly into runtime prompts."""
    formatted_history = []
    if chat_history_list:
        for msg in chat_history_list:
            if msg["role"] == "user":
                formatted_history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                formatted_history.append(AIMessage(content=msg["content"]))

    result = agent.invoke({
        "input": question,
        "chat_history": formatted_history
    })
    return result["output"]