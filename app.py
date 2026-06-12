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
import pandas as pd
from sqlalchemy import create_engine

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

# Shared helper engine to run structural diagnostic visualizations safely across threads
db_engine = create_engine(
    "sqlite:///company.db", 
    connect_args={"check_same_thread": False}
)

# --- UTILITY ENGINE: DYNAMIC AUTO-PLOTTING, DIAGNOSTICS & TEXT CLEANING ---
def parse_and_render_diagnostics(sql_query, text_response):
    """Parses executed queries to display syntax insights and render auto-plots if metrics exist."""
    # 1. Syntax Display Window
    st.markdown("### 📋 Query Plan Execution")
    st.code(sql_query, language="sql")
    
    # 2. Auto-Plotting Analytics Engine
    try:
        df = pd.read_sql_query(sql_query, db_engine)
        if not df.empty and len(df.columns) >= 2:
            # Look for a categorical column paired with a numeric value column
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            char_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            
            if numeric_cols and char_cols:
                x_axis = char_cols[0]
                y_axis = numeric_cols[0]
                
                st.markdown(f"### 📊 Automated Visual Analytics ({y_axis} by {x_axis})")
                chart_data = df.set_index(x_axis)[y_axis]
                st.bar_chart(chart_data)
    except Exception:
        pass # Silently proceed if the query is a scalar count or non-plottable format

def clean_conversational_text(text, sql_query):
    """Removes repetitive SQL code statements and raw queries from the conversational text."""
    if not sql_query:
        return text
    
    # Strip any native markdown triple-backtick code configurations
    text = re.sub(r"```sql.*?```", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL | re.IGNORECASE)
    
    # Clean up structural conversational configurations referencing raw execution loops
    text = text.replace(f'The SQL query "{sql_query}"', "The query")
    text = text.replace(f"The SQL query '{sql_query}'", "The query")
    text = text.replace(f'The SQL query `{sql_query}`', "The query")
    text = text.replace(sql_query, "")
    
    # Clean up double spacing fragments or awkward punctuation gaps left behind
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace('"" returns', 'returns').replace("'' returns", "returns")
    
    return text

# --- SIDEBAR GOVERNANCE PANEL ---
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
        # If diagnostics data exists in history payload, restore the rendering components
        if "sql" in msg:
            parse_and_render_diagnostics(msg["sql"], msg["content"])

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
                    db_schema = SQLDatabase(db_engine).get_table_info()
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
                    raw_response = exec_result["output"]
                    
                    # Clean conversational anomalies out of the response text
                    clean_response = clean_conversational_text(raw_response, final_sql)
                    
                    # Append response and diagnostic markers to history logs
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": clean_response,
                        "sql": final_sql
                    })
                    st.session_state.pending_sql_draft = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Execution Error: {str(e)}")

# ------------------ PATH B: STANDARD AUTOMATIC MODE ------------------
elif len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
    with st.spinner("Thinking..."):
        try:
            last_user_query = st.session_state.messages[-1]["content"]
            
            # Capture the full tool-chain output response block
            result = agent.invoke({"input": last_user_query})
            raw_response = result["output"]
            
            # Try to dynamically extract what query the agent executed under the hood for diagnostics
            extracted_query_string = ""
            for step in result.get("intermediate_steps", []):
                if isinstance(step, tuple) and len(step) > 0:
                    tool_action = step[0]
                    if hasattr(tool_action, 'tool_input') and 'query' in tool_action.tool_input:
                        extracted_query_string = tool_action.tool_input['query']
                        break
            
            # If standard regex pattern string fallback is required
            if not extracted_query_string:
                sql_find = re.search(r"(SELECT.*?;)", raw_response, re.DOTALL | re.IGNORECASE)
                if sql_find:
                    extracted_query_string = sql_find.group(1)
            
            # Scrub the matching inner query string text patterns out of verbal block
            clean_response = clean_conversational_text(raw_response, extracted_query_string)
            
            # Save assistant package to session message state history
            msg_payload = {"role": "assistant", "content": clean_response}
            if extracted_query_string:
                msg_payload["sql"] = extracted_query_string
                
            st.session_state.messages.append(msg_payload)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")