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

# Manage chat history rendering
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User prompt box interaction handling
if user_input := st.chat_input("Ask about the database..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Call our secure agent wrapper
                result = agent.invoke({"input": user_input})
                response = result["output"]
                st.markdown(response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )
            except Exception as e:
                # Catches your custom ValueError from security.py and prints a clean UI error block
                st.error(f"{str(e)}")