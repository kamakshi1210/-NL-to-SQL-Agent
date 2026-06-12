import sys
import importlib.util

# 1. Block importlib from scanning the broken torchvision package entirely
_original_find_spec = importlib.util.find_spec

def secure_find_spec(name, package=None):
    if name.startswith("torchvision"):
        return None  # Pretend it is absolutely not installed
    return _original_find_spec(name, package)

importlib.util.find_spec = secure_find_spec

# 2. Poison sys.modules cache so any direct 'import torchvision' safely fails instantly
sys.modules['torchvision'] = None
sys.modules['torchvision.io'] = None
sys.modules['torchvision.transforms'] = None
sys.modules['torchvision.transforms.v2'] = None


import streamlit as st
from database import create_database
from langchain_community.utilities import SQLDatabase
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import re

# Import the updated creation function from your agent file
from agent import create_agent

load_dotenv()

st.set_page_config(page_title="NL-to-SQL Agent", page_icon="🤖")
st.title("🤖 NL-to-SQL Agent")
st.caption("Ask questions about the company database in plain English!")

# Runs initial setup to seed the database with mock tables if they don't exist
create_database()

# Instantiate the custom secured agent we just configured in agent.py
if "agent" not in st.session_state:
    st.session_state.agent = create_agent()

agent = st.session_state.agent

# --- SIDEBAR GOVERNANCE PANEL (SUGGESTION 3) ---
st.sidebar.header("🛡️ Governance & Control")
expert_mode = st.sidebar.toggle(
    "Enable Expert Mode (HITL)", 
    value=False,
    help="When enabled, you must manually inspect and approve the generated SQL before execution."
)

if expert_mode:
    st.sidebar.info("💡 **Human-in-the-Loop Active:** The agent will pause for your explicit approval before querying the database.")
else:
    st.sidebar.success("⚡ **Auto-Pilot Active:** Queries execute automatically if they pass the internal security layers.")

st.sidebar.markdown("---")
st.sidebar.header("💡 Try asking:")
examples = [
    "How many employees are in Engineering?",
    "Who has the highest salary?",
    "What is the total sales amount in January 2024?",
    "List all employees from Indore",
    "Which department has the most employees?",
]
for ex in examples:
    st.sidebar.markdown(f"• {ex}")

# Initialize critical session states
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_sql_draft" not in st.session_state:
    st.session_state.pending_sql_draft = None

# Render permanent chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User prompt box interaction handling
user_input = st.chat_input("Ask about the database...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    # Reset any old pending drafts since a new question came in
    st.session_state.pending_sql_draft = None
    st.rerun()

# ------------------ PATH A: EXPERT MODE (HITL) STATE CONTROLLER ------------------
if expert_mode and len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
    
    # Generate the draft if we haven't built one for this question yet
    if st.session_state.pending_sql_draft is None:
        with st.spinner("Drafting SQL statement for review..."):
            try:
                last_user_query = st.session_state.messages[-1]["content"]
                
                # Safely unpack internal toolkit properties from LangChain wrapper
                toolkit = agent.tools[0].toolkit if hasattr(agent.tools[0], 'toolkit') else None
                if toolkit:
                    db_schema = toolkit.db.get_table_info()
                    llm_engine = toolkit.llm
                else:
                    from sqlalchemy import create_engine
                    engine = create_engine("sqlite:///file:company.db?mode=ro")
                    db_schema = SQLDatabase(engine).get_table_info()
                    llm_engine = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
                
                system_instructions = (
                    "You are a strict SQL code generator. Return ONLY a valid, executable SQLite "
                    "query based on the schema provided. Do not include markdown formatting like ```sql, "
                    "do not include explanations, and do not include conversational text.\n\n"
                    f"Database Schema:\n{db_schema}"
                )
                
                msg_response = llm_engine.invoke([
                    ("system", system_instructions),
                    ("user", f"Generate a SQL query to answer this: {last_user_query}")
                ])
                
                st.session_state.pending_sql_draft = msg_response.content.strip()
            except Exception as e:
                st.error(f"Drafting Error: {str(e)}")

    # Keep the widget block visible across script reloads until approval is confirmed!
    if st.session_state.pending_sql_draft:
        st.warning("📋 **Human-in-the-Loop Verification Required**")
        st.caption("Review or tweak the generated syntax below before authorization:")
        
        final_sql = st.text_area(
            "SQL Code Block Preview", 
            value=st.session_state.pending_sql_draft, 
            height=100,
            key="persistent_sql_editor"
        )
        
        if st.button("🔥 Approve & Run Query", type="primary", key="approve_action_btn"):
            with st.spinner("Executing user-authorized query..."):
                try:
                    execution_prompt = f"Run this exact SQL statement and summarize the results: {final_sql}"
                    exec_result = agent.invoke({"input": execution_prompt})
                    response = exec_result["output"]
                    
                    # Append response to history, wipe draft flag, and reset UI layout cleanly
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.session_state.pending_sql_draft = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Execution Error: {str(e)}")

# ------------------ PATH B: STANDARD AUTOMATIC MODE ------------------
elif len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
    with st.spinner("Thinking..."):
        try:
            last_user_query = st.session_state.messages[-1]["content"]
            result = agent.invoke({"input": last_user_query})
            response = result["output"]
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")