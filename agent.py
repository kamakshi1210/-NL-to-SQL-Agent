from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

def create_agent():
    db = SQLDatabase.from_uri("sqlite:///company.db")

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )

    agent = create_sql_agent(
        llm=llm,
        db=db,
        verbose=True,
        agent_type="tool-calling"
    )

    return agent

def ask_question(agent, question: str) -> str:
    result = agent.invoke({"input": question})
    return result["output"]