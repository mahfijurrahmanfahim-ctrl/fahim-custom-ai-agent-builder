
import streamlit as st
from google import genai
from google.genai import types

# ==========================================
# FAHIM AI AGENT BUILDER
# ==========================================

st.set_page_config(
    page_title="Fahim AI Agent",
    page_icon="🤖",
    layout="wide"
)

# ==========================================
# CONFIGURATION
# ==========================================

st.markdown("""
<style>
.stApp {
    background: #0b0b0f;
    color: #ffffff;
}
[data-testid="stChatMessage"] {
    border: 1px solid #292936;
    border-radius: 14px;
    padding: 12px;
}
.stChatInput {
    border-radius: 15px;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# API CONNECTION
# ==========================================

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]

    client = genai.Client(api_key=API_KEY)

except KeyError:
    st.error(
        "GEMINI_API_KEY is missing. "
        "Add it in Streamlit Cloud → App settings → Secrets."
    )
    st.stop()

except Exception as error:
    st.error(f"API connection setup failed: {error}")
    st.stop()

# ==========================================
# MODEL CONFIGURATION
# ==========================================

MODEL = st.secrets.get(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)

SYSTEM_INSTRUCTION = """
You are Fahim AI, an advanced and helpful AI assistant.

Your responsibilities:

1. Give accurate, useful and detailed answers.
2. Understand English and Bengali.
3. Follow the user's requested language.
4. Write directly in the chat.
5. Never invent facts, links or information.
6. Explain uncertainty honestly.
7. Help with programming, coding, AI, business,
   graphic design, writing and education.
8. When writing code, provide complete and
   properly formatted code when requested.
9. Remember the conversation context available
   in the current chat.
10. Avoid unnecessary short answers.
11. Explain technical instructions step by step.
12. Never claim to have performed actions you
    have not actually performed.

Be professional, intelligent, friendly and accurate.
"""

# ==========================================
# SESSION MEMORY
# ==========================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# HEADER
# ==========================================

st.title("🤖 FAHIM AI")
st.caption("Advanced AI Assistant | Powered by Google Gemini")

st.divider()

# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.title("⚙️ Settings")

    st.success("Gemini API configured")

    st.write("**Active model:**")
    st.code(MODEL)

    st.write(
        f"**Messages:** {len(st.session_state.messages)}"
    )

    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.markdown("""
    ### Features

    - AI Chat
    - Bengali and English
    - Programming assistance
    - Business support
    - Creative writing
    - Technical explanations
    - Conversation history
    """)

    st.divider()

    st.caption("FAHIM GRAPHIC DESIGN")
    st.caption("Creative Design. Professional Results.")

# ==========================================
# DISPLAY CHAT HISTORY
# ==========================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

# ==========================================
# CHAT INPUT
# ==========================================

user_prompt = st.chat_input(
    "Ask Fahim AI anything..."
)

# ==========================================
# GENERATE AI RESPONSE
# ==========================================

if user_prompt:

    # Save user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_prompt
    })

    # Display user message
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Prepare conversation for Gemini
    api_history = []

    for message in st.session_state.messages:

        api_role = (
            "user"
            if message["role"] == "user"
            else "model"
        )

        api_history.append(
            types.Content(
                role=api_role,
                parts=[
                    types.Part(text=message["content"])
                ]
            )
        )

    # Generate response
    with st.chat_message("assistant"):

        with st.spinner("Fahim AI is thinking..."):

            try:

                response = client.models.generate_content(
                    model=MODEL,
                    contents=api_history,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.7
                    )
                )

                answer = response.text

                if not answer:
                    answer = (
                        "The model returned no text. "
                        "Please try another question."
                    )

                st.markdown(answer)

                # Save AI response
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

            except Exception as error:

                st.error(
                    "Gemini request failed. "
                    "Please check your API access, model "
                    "availability and usage limits."
                )

                st.code(str(error))

                # Remove failed user message
                st.session_state.messages.pop()

# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "© FAHIM AI | Powered by Google Gemini API"
)
