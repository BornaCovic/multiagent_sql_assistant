import asyncio
import streamlit as st

from kostur import run_query_chat

st.set_page_config(page_title="VideoStore helper", page_icon="🎥")
st.title("🎥 VideoStore Helper")

query = st.text_input("How can I help you?")


if st.button("Search") and query:

    async def _runner() -> None:
        chat_placeholder = st.container()
        async for frame in run_query_chat(query):
            role, *rest = frame.split(":", 1)
            content = rest[0].strip() if rest else ""
            with chat_placeholder:
                with st.chat_message("assistant"):
                    st.markdown(f"**{role}**: {content}")

    with st.spinner("Working …"):
        try:
            asyncio.run(_runner())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_runner())

    st.success("Answer complete 🎉")