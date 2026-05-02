from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

def create_agent():
    db = SQLDatabase.from_uri("sqlite:///company.db")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        google_api_key=os.getenv("OPENAI_API_KEY")
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