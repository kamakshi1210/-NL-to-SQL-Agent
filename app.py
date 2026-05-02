import streamlit as st
from database import create_database
from agent import create_agent, ask_question

st.set_page_config(page_title="NL-to-SQL Agent", page_icon="🤖")
st.title("🤖 NL-to-SQL Agent")
st.caption("Ask questions about the company database in plain English!")

create_database()

@st.cache_resource
def load_agent():
    return create_agent()

agent = load_agent()

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

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("Ask about the database..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = ask_question(agent, user_input)
                st.markdown(response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )
            except Exception as e:
                st.error(f"Error: {str(e)}")