import streamlit as st
from google import genai
from google.genai import types

# ==========================================
# FAHIM AI - FAST STREAMING ENGINE
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

    if not API_KEY:
        st.error("Gemini API key is empty.")
        st.stop()

except KeyError:
    st.error(
        "GEMINI_API_KEY is missing. "
        "Add it in Streamlit Cloud → Settings → Secrets."
    )
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

# Keep recent conversation context.
# Full conversation remains visible in the interface.
MAX_CONTEXT_MESSAGES = 12

SYSTEM_INSTRUCTION = """
You are Fahim AI, an advanced AI assistant.

IDENTITY:
You are Fahim AI, a powerful, intelligent,
professional and helpful AI assistant.

CORE RESPONSIBILITIES:

1. Give accurate, useful and detailed answers.
2. Understand Bengali and English.
3. Follow the language requested by the user.
4. Answer directly inside the chat.
5. Never invent facts, sources or links.
6. Explain uncertainty honestly.
7. Help with programming, AI, business,
   graphic design, writing and education.
8. When code is requested, provide complete,
   working and properly formatted code.
9. Use available conversation history.
10. Avoid unnecessary restrictions on answer length.
11. Explain technical instructions step by step.
12. Never claim to perform actions you did not perform.
13. Understand the user's actual question before answering.
14. Avoid unnecessary introductions and repetition.
15. Provide professional, practical solutions.

PERSONAL PROFILE:
Use the user's available profile information
when it is relevant to the question.

IMPORTANT:
Do not invent missing personal information.
Do not claim live internet access unless
a search tool is actually available.
"""

# ==========================================
# CACHED GEMINI CLIENT
# ==========================================

@st.cache_resource(show_spinner=False)
def get_client(api_key):
    return genai.Client(api_key=api_key)


try:
    client = get_client(API_KEY)

except Exception as error:
    st.error("Gemini client initialization failed.")
    st.code(str(error))
    st.stop()

# ==========================================
# SESSION MEMORY
# ==========================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_model" not in st.session_state:
    st.session_state.last_model = PRIMARY_MODEL

# ==========================================
# ERROR DETECTION
# ==========================================

def is_auth_error(error):
    message = str(error).upper()

    return any(code in message for code in [
        "401",
        "403",
        "API_KEY_INVALID",
        "PERMISSION_DENIED"
    ])


def is_temporary_error(error):
    message = str(error).upper()

    return any(code in message for code in [
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
    ])


# ==========================================
# OPTIMIZED CONVERSATION HISTORY
# ==========================================

def prepare_history(messages):

    recent_messages = messages[-MAX_CONTEXT_MESSAGES:]

    # Gemini conversation should start with a user message.
    while (
        recent_messages
        and recent_messages[0]["role"] != "user"
    ):
        recent_messages = recent_messages[1:]

    contents = []

    for message in recent_messages:

        role = (
            "user"
            if message["role"] == "user"
            else "model"
        )

        contents.append(
            types.Content(
                role=role,
                parts=[
                    types.Part(text=message["content"])
                ]
            )
        )

    return contents


# ==========================================
# FAST STREAMING + AUTOMATIC FALLBACK
# ==========================================

def generate_stream(contents, output_placeholder):

    errors = []

    for model_name in MODELS:

        answer_parts = []

        try:

            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )

            stream = client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=config
            )

            for chunk in stream:

                chunk_text = chunk.text

                if chunk_text:

                    answer_parts.append(chunk_text)

                    # Display text immediately.
                    output_placeholder.markdown(
                        "".join(answer_parts)
                    )

            answer = "".join(answer_parts)

            if not answer.strip():
                raise RuntimeError(
                    "Model returned an empty response."
                )

            st.session_state.last_model = model_name

            return answer, model_name, None

        except Exception as error:

            errors.append(
                f"{model_name}: {error}"
            )

            # Never retry an invalid API key.
            if is_auth_error(error):
                raise error

            # If generation has already started,
            # keep the partial answer instead of
            # generating duplicate text with another model.
            if answer_parts:

                partial_answer = "".join(answer_parts)

                return (
                    partial_answer,
                    model_name,
                    "Generation stopped before completion: "
                    + str(error)
                )

            # Switch immediately to the next model.
            output_placeholder.empty()

            continue

    raise RuntimeError(
        "All available Gemini models failed.\n\n"
        + "\n".join(errors)
    )


# ==========================================
# HEADER
# ==========================================

st.title("🤖 FAHIM AI")

st.caption(
    "Advanced AI Assistant | Fast Streaming | Google Gemini"
)

st.divider()

# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.title("⚙️ Settings")

    st.success("Gemini API connected")

    st.write("**Primary model**")
    st.code(PRIMARY_MODEL)

    st.write("**Backup models**")

    for model in BACKUP_MODELS:
        st.caption(f"• {model}")

    st.divider()

    st.write(
        f"**Total messages:** "
        f"{len(st.session_state.messages)}"
    )

    st.write(
        f"**Current model:** "
        f"{st.session_state.last_model}"
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

    - Fast streaming responses
    - Bengali and English
    - Advanced AI assistance
    - Programming and coding
    - Business support
    - Creative design assistance
    - Conversation memory
    - Smart history optimization
    - Automatic model fallback
    - Error recovery
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

    # Prepare only recent conversation context.
    api_history = prepare_history(
        st.session_state.messages
    )

    with st.chat_message("assistant"):

        output_placeholder = st.empty()

        try:

            answer, used_model, stream_error = generate_stream(
                api_history,
                output_placeholder
            )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

            if used_model != PRIMARY_MODEL:

                st.info(
                    f"Backup model used: {used_model}"
                )

            if stream_error:

                st.warning(stream_error)

        except Exception as error:

            output_placeholder.empty()

            st.error(
                "Fahim AI could not generate a response. "
                "Please try again."
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
