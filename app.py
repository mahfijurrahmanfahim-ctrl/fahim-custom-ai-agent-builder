import streamlit as st
import uuid
from google import genai
from google.genai import types
from supabase import create_client

# ==========================================
# FAHIM AI - PERMANENT MEMORY ENGINE
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
# CONFIGURATION
# ==========================================

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_SECRET_KEY"]

    if not all([GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
        st.error("One or more API credentials are empty.")
        st.stop()

except KeyError as error:
    st.error(f"Missing Streamlit Secret: {error}")
    st.stop()

PRIMARY_MODEL = st.secrets.get(
    "PRIMARY_MODEL",
    "gemini-3.8-flash"
)

BACKUP_MODELS = list(
    st.secrets.get(
        "BACKUP_MODELS",
        ["gemini-3.7-flash", "gemini-3.6-flash"]
    )
)

MODELS = list(dict.fromkeys(
    [PRIMARY_MODEL] + BACKUP_MODELS
))

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
13. Understand the user's actual question.
14. Avoid unnecessary introductions and repetition.

PERSONAL PROFILE:
Use the user's available profile information
when relevant.

IMPORTANT:
Do not invent missing personal information.
Do not claim live internet access unless
a search tool is actually available.
"""

# ==========================================
# AI CLIENT
# ==========================================

@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)


# ==========================================
# SUPABASE CLIENT
# ==========================================

@st.cache_resource(show_spinner=False)
def get_supabase_client(url, key):
    return create_client(url, key)


try:
    client = get_gemini_client(GEMINI_API_KEY)
    supabase = get_supabase_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

except Exception as error:
    st.error("Database or AI connection failed.")
    st.code(str(error))
    st.stop()

# ==========================================
# PERMANENT SESSION ID
# ==========================================

def get_session_id():

    existing_id = st.query_params.get("sid")

    if existing_id:
        try:
            return str(uuid.UUID(existing_id))
        except ValueError:
            pass

    new_id = str(uuid.uuid4())
    st.query_params["sid"] = new_id

    return new_id


SESSION_ID = get_session_id()

# ==========================================
# DATABASE FUNCTIONS
# ==========================================

def load_chat_history():

    try:
        result = (
            supabase
            .table("chat_history")
            .select("role, content")
            .eq("session_id", SESSION_ID)
            .order("created_at")
            .execute()
        )

        return result.data or []

    except Exception as error:
        st.error("Could not load saved chat history.")
        st.code(str(error))
        return None


def save_message(role, content):

    try:
        supabase.table("chat_history").insert({
            "session_id": SESSION_ID,
            "role": role,
            "content": content
        }).execute()

        return True

    except Exception as error:
        st.error("Message could not be saved to database.")
        st.code(str(error))
        return False


def delete_chat_history():

    try:
        supabase.table("chat_history").delete().eq(
            "session_id",
            SESSION_ID
        ).execute()

        return True

    except Exception as error:
        st.error("Could not delete saved conversation.")
        st.code(str(error))
        return False


# ==========================================
# LOAD PERMANENT MEMORY
# ==========================================

if "messages" not in st.session_state:

    saved_messages = load_chat_history()

    if saved_messages is None:
        st.error(
            "FAHIM AI could not access its database. "
            "Please check your Supabase settings."
        )
        st.stop()

    st.session_state.messages = saved_messages

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


# ==========================================
# CONVERSATION HISTORY
# ==========================================

def prepare_history(messages):

    recent_messages = messages[-MAX_CONTEXT_MESSAGES:]

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
# STREAMING ENGINE + FALLBACK
# ==========================================

def generate_stream(contents, placeholder):

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

                    placeholder.markdown(
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

            if is_auth_error(error):
                raise error

            if answer_parts:

                return (
                    "".join(answer_parts),
                    model_name,
                    str(error)
                )

            placeholder.empty()

    raise RuntimeError(
        "All Gemini models failed:\n"
        + "\n".join(errors)
    )


# ==========================================
# HEADER
# ==========================================

st.title("🤖 FAHIM AI")

st.caption(
    "Advanced AI Assistant | Permanent Memory | Gemini"
)

st.divider()

# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.title("⚙️ Settings")

    st.success("Gemini API connected")
    st.success("Supabase database connected")
    st.success("Permanent memory enabled")

    st.write("**Primary model**")
    st.code(PRIMARY_MODEL)

    st.write("**Backup models**")

    for model in BACKUP_MODELS:
        st.caption(f"• {model}")

    st.divider()

    st.write(
        f"**Total messages:** {len(st.session_state.messages)}"
    )

    st.write(
        f"**Current model:** {st.session_state.last_model}"
    )

    st.divider()

    if st.button(
        "🗑️ Clear conversation",
        use_container_width=True
    ):

        if delete_chat_history():

            st.session_state.messages = []

            st.success("Conversation deleted.")
            st.rerun()

    st.divider()

    st.markdown("""
    ### Features

    - Permanent chat history
    - Automatic database saving
    - Restore conversations
    - Bengali and English
    - Fast Gemini streaming
    - Automatic model fallback
    - Programming assistance
    - Business support
    - Creative design assistance
    """)

    st.divider()

    st.caption("FAHIM GRAPHIC DESIGN")
    st.caption("Creative Design. Professional Results.")

# ==========================================
# DISPLAY SAVED CHAT
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
# GENERATE AND SAVE
# ==========================================

if user_prompt:

    # Save user message to permanent database.
    user_saved = save_message(
        "user",
        user_prompt
    )

    st.session_state.messages.append({
        "role": "user",
        "content": user_prompt
    })

    with st.chat_message("user"):
        st.markdown(user_prompt)

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

            # Save assistant response permanently.
            assistant_saved = save_message(
                "assistant",
                answer
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
                st.warning(
                    "Response generation was interrupted: "
                    + stream_error
                )

            if assistant_saved:
                st.caption("☁️ Saved to permanent memory")

        except Exception as error:

            output_placeholder.empty()

            st.error(
                "Fahim AI could not generate a response."
            )

            with st.expander("Technical error details"):
                st.code(str(error))

# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "© FAHIM AI | Powered by Google Gemini and Supabase"
)
