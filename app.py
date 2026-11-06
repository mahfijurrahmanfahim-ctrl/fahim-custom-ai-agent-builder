import streamlit as st
import time
from google import genai
from google.genai import types

# ==========================================
# FAHIM AI - ADVANCED CHAT ASSISTANT
# ==========================================

st.set_page_config(
    page_title="Fahim AI",
    page_icon="🤖",
    layout="wide"
)

# ==========================================
# DESIGN
# ==========================================

st.markdown("""
<style>
.stApp {
    background: #0b0b0f;
    color: white;
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
# API CONFIGURATION
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

except Exception:
    st.error("Gemini API client initialization failed.")
    st.stop()

# ==========================================
# MODEL CONFIGURATION
# ==========================================

PRIMARY_MODEL = st.secrets.get(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)

BACKUP_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash"
]

MODELS = list(dict.fromkeys(
    [PRIMARY_MODEL] + BACKUP_MODELS
))

SYSTEM_INSTRUCTION = """
You are Fahim AI, an advanced AI assistant.

Your responsibilities:

1. Give accurate, helpful and detailed answers.
2. Understand Bengali and English.
3. Follow the language requested by the user.
4. Answer directly inside the chat.
5. Never invent facts, links or information.
6. Explain uncertainty honestly.
7. Help with programming, AI, business,
   graphic design, writing and education.
8. When code is requested, provide complete,
   working and properly formatted code.
9. Use the conversation history available to you.
10. Avoid unnecessarily short answers.
11. Explain technical instructions step by step.
12. Never claim to perform actions you did not perform.

Be intelligent, professional, friendly and accurate.
"""

# ==========================================
# SESSION MEMORY
# ==========================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# ERROR DETECTION
# ==========================================

def is_temporary_error(error):

    error_text = str(error).upper()

    temporary_codes = [
        "429",
        "500",
        "502",
        "503",
        "504",
        "UNAVAILABLE",
        "RESOURCE_EXHAUSTED",
        "INTERNAL",
        "DEADLINE_EXCEEDED",
        "TIMEOUT"
    ]

    return any(
        code in error_text
        for code in temporary_codes
    )


def is_auth_error(error):

    error_text = str(error).upper()

    auth_codes = [
        "401",
        "403",
        "API_KEY_INVALID",
        "PERMISSION_DENIED"
    ]

    return any(
        code in error_text
        for code in auth_codes
    )


# ==========================================
# SMART MODEL FALLBACK
# ==========================================

def generate_ai_response(contents):

    last_error = None

    for model_index, model_name in enumerate(MODELS):

        # Primary model gets one automatic retry.
        # Backup models get one attempt each.
        max_attempts = 2 if model_index == 0 else 1

        for attempt in range(max_attempts):

            try:

                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.7
                    )
                )

                answer = response.text

                if not answer:
                    raise RuntimeError(
                        "The model returned an empty response."
                    )

                return answer, model_name

            except Exception as error:

                last_error = error

                # Do not retry invalid credentials.
                if is_auth_error(error):
                    raise error

                # Retry temporary errors with a short delay.
                if (
                    is_temporary_error(error)
                    and attempt + 1 < max_attempts
                ):
                    time.sleep(2 ** (attempt + 1))
                    continue

                # Move to the next model.
                break

    raise RuntimeError(
        "All Gemini models failed. "
        "Please try again later. "
        f"Last error: {last_error}"
    )


# ==========================================
# HEADER
# ==========================================

st.title("🤖 FAHIM AI")

st.caption(
    "Advanced AI Assistant | Powered by Google Gemini"
)

st.divider()

# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.title("⚙️ Settings")

    st.success("Gemini API client initialized")

    st.write("**Primary model:**")
    st.code(PRIMARY_MODEL)

    st.write("**Backup models:**")

    for backup in BACKUP_MODELS:
        st.caption(f"• {backup}")

    st.write(
        f"**Messages:** {len(st.session_state.messages)}"
    )

    if st.button(
        "🗑️ Clear conversation",
        use_container_width=True
    ):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.markdown("""
    ### Features

    - Advanced AI Chat
    - Bengali and English
    - Programming assistance
    - Business support
    - Creative writing
    - Technical explanations
    - Conversation history
    - Automatic retry
    - Backup model switching
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
# GENERATE RESPONSE
# ==========================================

if user_prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": user_prompt
    })

    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Prepare conversation history.
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

    with st.chat_message("assistant"):

        with st.spinner(
            "Fahim AI is thinking..."
        ):

            try:

                answer, used_model = generate_ai_response(
                    api_history
                )

                st.markdown(answer)

                if used_model != PRIMARY_MODEL:
                    st.info(
                        f"Backup model used: {used_model}"
                    )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

            except Exception as error:

                st.error(
                    "Fahim AI could not generate a response. "
                    "Please try again later."
                )

                with st.expander("Technical error details"):
                    st.code(str(error))

                # Remove failed user message.
                st.session_state.messages.pop()

# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "© FAHIM AI | Powered by Google Gemini API"
)
