import streamlit as st
import uuid
import time
import threading
import queue
from google import genai
from google.genai import types
from supabase import create_client

# ==========================================
# FAHIM AI - ADVANCED STREAMING ENGINE
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
[data-testid="stStatusWidget"] {
    border: 1px solid #343444;
    border-radius: 12px;
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
        st.error("One or more credentials are empty.")
        st.stop()

except KeyError as error:
    st.error(f"Missing Streamlit Secret: {error}")
    st.stop()

PRIMARY_MODEL = st.secrets.get(
    "PRIMARY_MODEL",
    "gemini-3.8-flash"
)

backup_config = st.secrets.get(
    "BACKUP_MODELS",
    ["gemini-3.7-flash", "gemini-3.6-flash"]
)

if isinstance(backup_config, str):
    BACKUP_MODELS = [
        item.strip()
        for item in backup_config.split(",")
        if item.strip()
    ]
else:
    BACKUP_MODELS = list(backup_config)

MODELS = list(dict.fromkeys(
    [PRIMARY_MODEL] + BACKUP_MODELS
))

MAX_CONTEXT_MESSAGES = 12
STREAM_TIMEOUT = 180

SYSTEM_INSTRUCTION = """
You are Fahim AI, an advanced AI assistant.

IDENTITY:
You are Fahim AI, a powerful, intelligent,
professional and helpful AI assistant.

CORE RESPONSIBILITIES:

1. Give accurate and useful answers.
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
10. Avoid unnecessary introductions and repetition.
11. Explain technical instructions step by step.
12. Never claim to perform actions you did not perform.
13. Understand the user's actual question.
14. Do not invent missing personal information.
15. Do not claim live internet access unless
    a search tool is actually available.

PERSONAL PROFILE:
Use the user's available profile information
when relevant.
"""

# ==========================================
# CLIENTS
# ==========================================

@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)


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
    st.error("AI or database connection failed.")
    st.exception(error)
    st.stop()

# ==========================================
# SESSION
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
# DATABASE
# ==========================================

def load_chat_history():

    result = (
        supabase
        .table("chat_history")
        .select("role, content")
        .eq("session_id", SESSION_ID)
        .order("created_at")
        .execute()
    )

    return result.data or []


def save_message(role, content):

    try:
        supabase.table("chat_history").insert({
            "session_id": SESSION_ID,
            "role": role,
            "content": content
        }).execute()

        return True

    except Exception as error:
        st.error(f"Database save failed: {error}")
        return False


def delete_chat_history():

    try:
        supabase.table("chat_history").delete().eq(
            "session_id", SESSION_ID
        ).execute()

        return True

    except Exception as error:
        st.error(f"Delete failed: {error}")
        return False


# ==========================================
# LOAD MEMORY
# ==========================================

if "messages" not in st.session_state:

    try:
        st.session_state.messages = load_chat_history()

    except Exception as error:
        st.error("Could not restore permanent chat history.")
        st.exception(error)
        st.stop()


if "last_model" not in st.session_state:
    st.session_state.last_model = PRIMARY_MODEL

if "request_count" not in st.session_state:
    st.session_state.request_count = 0

# ==========================================
# ERROR DETECTION
# ==========================================

def is_auth_error(error):

    message = str(error).upper()

    return any(code in message for code in [
        "API_KEY_INVALID",
        "401",
        "INVALID API KEY",
        "UNAUTHENTICATED"
    ])


# ==========================================
# CHAT HISTORY
# ==========================================

def prepare_history(messages):

    recent = messages[-MAX_CONTEXT_MESSAGES:]

    while recent and recent[0]["role"] != "user":
        recent = recent[1:]

    contents = []

    for message in recent:

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
# STREAM WORKER
# ==========================================

def stream_worker(model_name, contents, event_queue):

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

            try:
                text = chunk.text
            except Exception:
                text = None

            if text:
                event_queue.put(("chunk", text))

        event_queue.put(("complete", None))

    except Exception as error:
        event_queue.put(("error", str(error)))


# ==========================================
# ADVANCED STREAMING + FALLBACK
# ==========================================

def generate_answer(contents, answer_placeholder, status):

    errors = []

    for index, model_name in enumerate(MODELS):

        is_backup = index > 0

        status.update(
            label=(
                f"Switching to backup model: {model_name}"
                if is_backup
                else f"Connecting to primary model: {model_name}"
            ),
            state="running",
            expanded=True
        )

        event_queue = queue.Queue()

        worker = threading.Thread(
            target=stream_worker,
            args=(model_name, contents, event_queue),
            daemon=True
        )

        worker.start()

        answer_parts = []
        started = time.monotonic()
        last_update = started
        completed = False
        failed = False
        error_message = None

        status.write(f"Model: {model_name}")
        status.write("Waiting for AI response...")

        while True:

            now = time.monotonic()

            if now - started > STREAM_TIMEOUT:
                error_message = (
                    f"Response timed out after {STREAM_TIMEOUT} seconds."
                )
                failed = True
                break

            try:
                event, value = event_queue.get(timeout=0.5)

            except queue.Empty:

                elapsed = int(time.monotonic() - started)

                if now - last_update >= 2:

                    if answer_parts:
                        status.write(
                            f"Generating response... {elapsed}s elapsed"
                        )
                    else:
                        status.write(
                            f"Waiting for first response... {elapsed}s elapsed"
                        )

                    last_update = now

                continue

            if event == "chunk":

                answer_parts.append(value)

                answer_placeholder.markdown(
                    "".join(answer_parts) + " ▌"
                )

            elif event == "complete":

                completed = True
                break

            elif event == "error":

                failed = True
                error_message = value
                break

        answer = "".join(answer_parts)

        if completed and answer.strip():

            answer_placeholder.markdown(answer)

            st.session_state.last_model = model_name

            status.update(
                label=f"Response completed using {model_name}",
                state="complete",
                expanded=False
            )

            return answer, model_name, None

        # Never treat an interrupted response as complete.
        answer_placeholder.empty()

        if failed:
            errors.append(
                f"{model_name}: {error_message}"
            )

        elif not answer.strip():
            errors.append(
                f"{model_name}: Empty response returned."
            )

        if error_message and is_auth_error(error_message):
            break

        if index < len(MODELS) - 1:

            status.update(
                label=f"{model_name} failed. Trying backup...",
                state="running",
                expanded=True
            )

    status.update(
        label="All available AI models failed.",
        state="error",
        expanded=True
    )

    raise RuntimeError(
        "\n\n".join(errors) or "No model returned a valid response."
    )


# ==========================================
# HEADER
# ==========================================

st.title("🤖 FAHIM AI")

st.caption(
    "Advanced AI Assistant | Permanent Memory | Gemini Streaming"
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

    st.divider()

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

    st.write(
        f"**Requests:** {st.session_state.request_count}"
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
    - Live response streaming
    - Live processing status
    - Automatic model fallback
    - Programming assistance
    - Business support
    - Creative design assistance
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

    st.session_state.request_count += 1

    # Save user message
    user_saved = save_message("user", user_prompt)

    st.session_state.messages.append({
        "role": "user",
        "content": user_prompt
    })

    with st.chat_message("user"):
        st.markdown(user_prompt)

    if not user_saved:
        st.warning(
            "Your message is currently in this session, "
            "but permanent database saving failed."
        )

    api_history = prepare_history(
        st.session_state.messages
    )

    with st.chat_message("assistant"):

        output_placeholder = st.empty()

        try:

            with st.status(
                "FAHIM AI is starting...",
                expanded=True
            ) as status:

                answer, used_model, stream_error = generate_answer(
                    api_history,
                    output_placeholder,
                    status
                )

            # Save only completed response.
            assistant_saved = save_message(
                "assistant",
                answer
            )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

            st.caption(f"⚡ Model: {used_model}")

            if used_model != PRIMARY_MODEL:
                st.info(
                    f"Backup model successfully used: {used_model}"
                )

            if assistant_saved:
                st.caption(
                    "☁️ Permanently saved to Supabase"
                )
            else:
                st.warning(
                    "Response generated, but database saving failed."
                )

        except Exception as error:

            st.error(
                "FAHIM AI could not complete your response."
            )

            with st.expander("Technical error details", expanded=True):
                st.code(str(error))

            st.info(
                "Please check your Gemini API key, model names, "
                "API quota and network connection."
            )

# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "© FAHIM AI | Powered by Google Gemini and Supabase"
)
