import sqlite3
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits import create_sql_agent
from langchain_groq import ChatGroq
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

    # Create the agent providing both 'db' (to satisfy LangChain) and your custom 'tools'
    agent = create_sql_agent(
        llm=llm,
        db=db,             # Satisfies the requirement constraint
        tools=tools,       # Overrides defaults with your secured tools list
        verbose=True,
        agent_type="tool-calling"
    )

    return agent

# Standalone helper function for testing
def ask_question(agent, question: str) -> str:
    result = agent.invoke({"input": question})
    return result["output"]