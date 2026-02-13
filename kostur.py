import psycopg2
import asyncio
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
import os
from autogen_agentchat.agents import (AssistantAgent, UserProxyAgent)
from autogen_core.tools import FunctionTool
from autogen_agentchat.teams import SelectorGroupChat
from typing import AsyncGenerator, Dict, List
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.conditions import MaxMessageTermination,TextMentionTermination

text_mention_termination = TextMentionTermination("TERMINATE")
max_messages_termination = MaxMessageTermination(max_messages=20)
combined_termination = text_mention_termination | max_messages_termination

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
model_client = OpenAIChatCompletionClient(model='gpt-5-mini', api_key=api_key)

def execute_query(gen_query: str):
    conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="sakila",
    user="sakila",
    password="p_ssW0rd",
    )
    try:
        cur = conn.cursor()
        cur.execute(gen_query)
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        return {"columns": colnames, "rows": rows}
    except Exception as exc:
        return{"error": str(exc)}
    finally:
        cur.close()
        conn.close()

def build_team() -> SelectorGroupChat:

    query_tool = FunctionTool(execute_query, description="Execute the given SQL SELECT query on the sakila database and return the results as {'columns': [...], 'rows': [...]}.")

    sql_assistant = AssistantAgent(
        name="sql_assistant",
        model_client=model_client,
        system_message=(
            "You are a helpful assistant that generates SQL queries based on natural language.\n"
            "Only respond with the SQL query, no extra text.\n"
            "Never use INSERT, UPDATE, DELETE, DROP or other non-SELECT statements.\n"
            '''The database contains the following tables(and their columns): FILM(FILM_ID, TITLE,DESCRIPTION, RELEASE_YEAR, LANGUAGE_ID, ORIGINAL_LANGUAGE_ID, RENTAL_DURATION, RENTAL_RATE, LENGTH, REPLACEMENT_COST, RATING)
            ACTOR(ACTOR_ID, FIRST_NAME, LAST_NAME), CATEGORY(CATEGORY_ID, NAME), FILM_CATEGORY(FILM_ID, CATEGORY_ID), FILM_ACTOR(ACTOR_ID, FILM_ID), INVENTORY(INVENTORY_ID, FILM_ID, STORE_ID), STORE(STORE_ID, MANAGER_STAFF_ID, ADDRESS_ID),
            ADDRESS(ADDRESS_ID, ADDRESSM ADDRESS2, DISTRICT, CITY_ID, POSTAL_CODE, PHONE), STAFF(STAFF_ID, FIRST_NAME, LAST_NAME, ADDRESS_ID, PICTURE, EMAIL, STORE_ID, ACTIVE, USERNAME, PASSWORD), PAYMENT(PAYMENT_ID, CUSTOMER_ID, STAFF_ID, RENTAL_ID, AMOUNT, PAYMENT_DATE),
            RENTAL(RENTAL_ID, RENTAL_DATE, iNVENTORY_ID, CUSTOMER_ID, RETURN_DATE, STAFF_ID), CUSTOMER(CUSTOMER_ID, STORE_ID, FIRST_NAME, LAST_NAME, EMAIL, ADDRESS_ID, ACTIVE, CREATE_DATE), CITY(CITY_ID, CITY, COUNTRY_ID), COUNTRY(COUNTRY_ID, COUNTRY)
            '''
        ),
        description="An agent that creates the SQL query from natural language inputs"
    )

    sql_runner = AssistantAgent(
        name="sql_runner",
        model_client=model_client,
        system_message=(
            "You receive a valid SQL SELECT query as input.\n"
            "Always call the `execute_query` tool with that query.\n"
            "Do not rewrite or explain the query, just run it using the tool."
        ),
        tools=[query_tool],
        reflect_on_tool_use=True,
        description="An agent that runs the previously created SQL query using a tool"
    )

    result_translator = AssistantAgent(
        name="result_translator",
        model_client=model_client,
        system_message=("You receive the raw SQL result as a dictionary with columns and rows as keys from the previous agent.\n"
            "Summarize them in clear, concise natural language for a human non technical user.\n"
            "If the result is a table, you may describe patterns or highlight key rows.\n"
            "You can also describe a logical conclusion you derived from the data.\n"
            "Respond with ONE answer, and do not give alternative phrasings.\n"
            "After your final answer output the word TERMINATE in a new line."),
        description="An agent that takes the output of the SQL query and transforms it into human readable text output"
    )

    selector_prompt = '''
    Select an agent to perform the task.

    {roles}

    Current conversation history :
    {history}

    Read the above conversation, then select an agent from {participants} to perform the next task.
    - If you have a natural language request, select "sql_assistant".
    - If you have an SQL query ready, select "sql_runner".
    - If you have raw SQL result dictionary, select "result_translator".
    - If the "result_translator" has answered, stop further communication.
    Only select one agent.
    '''

    selector_team = SelectorGroupChat(
        participants=[sql_assistant, sql_runner, result_translator],
        model_client=model_client,
        termination_condition=combined_termination,
        selector_prompt=selector_prompt,
        allow_repeated_speaker=True)
    
    return selector_team, result_translator.name

async def run_query_chat(
    question: str,
) -> AsyncGenerator[str, None]:
    """Yield strings representing the conversation in real‑time."""

    task_prompt = (
        f"Create an SQL query based on **{question}** and return a valid and easy to read description of the result."
        f"Only the natural language output should be presented to the user."
    )

    selector_team, transl_assistant_name = build_team()

    async for msg in selector_team.run_stream(task=task_prompt):
        if isinstance(msg, TextMessage) and msg.source == transl_assistant_name:
            yield f"{msg.source}: {msg.content}"
            break


if __name__ == "__main__":
    async def _demo() -> None:
        async for line in run_query_chat("Koliko je zaradeno po filmu jucer"):
            print(line)

    asyncio.run(_demo()) 