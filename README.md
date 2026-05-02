# NL-to-SQL Agent 🤖

An AI-powered chatbot that converts plain English questions into SQL queries and returns answers from a real database.

## What it does
- User types a question in plain English
- LangChain converts it to SQL automatically
- Queries a real SQLite database
- Returns the answer in plain English

## Tech Stack
- Python
- LangChain
- Groq (LLM)
- SQLite
- Streamlit

## How to run
1. Clone the repo
2. Install dependencies: pip install -r requirements.txt
3. Add your GROQ_API_KEY in .env file
4. Run: streamlit run app.py

## Sample Questions
- Who has the highest salary?
- How many employees are in Engineering?
- List all employees from Indore
- What is the total sales in January 2024?