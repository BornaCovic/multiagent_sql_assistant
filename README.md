# VideoStore AI Helper – Multi-Agent SQL Assistant
## An AI based system that converts natural language queries into SQL, executes them on a PostgreSQL database, and returns human-readable results through a Streamlit interface. The project demonstrates multiagent orchestration and tool based query execution using LLMs.

## Features

- Natural language to SQL query generation  
- Automatic SQL execution on a PostgreSQL (Sakila) database  
- Multiagent workflow (query generation → execution → result summarization)  
- Tool based query execution via controlled function calls  
- Real-time streaming responses in the UI  
- Streamlit based web interface  
- Restriction to `SELECT` statements for safe database interaction

## Architecture

The system follows a multi-agent pipeline architecture:

1. **SQL Assistant Agent**  
   Converts natural language input into a valid SQL `SELECT` query.

2. **SQL Runner Agent**  
   Executes the generated query using a database tool interface.

3. **Result Translator Agent**  
   Transforms raw database results (columns and rows) into sensible, human-readable output.

Agent coordination is handled by a selection based orchestration mechanism 
that dynamically chooses the next agent based on conversation state.  
The frontend is implemented in Streamlit and streams responses asynchronously to the user.
