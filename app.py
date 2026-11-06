
import streamlit as st
import uuid
import time

from google import genai
from google.genai import types
from supabase import create_client
from openai import OpenAI

# ==================================================
# FAHIM AI - HYBRID MULTI-PROVIDER EDITION
# ==================================================

st.set_page_config(
    page_title="FAHIM AI",
    page_icon="🤖",
    layout="wide"
)

# ==================================================
# DESIGN
# ==================================================

st.markdown("""
<style>
.stApp {
    background: #0b0b0f;
    color: #ffffff;
}

[data-testid="stChatMessage"] {
    border: 1px solid #292936;
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 10px;
}

.stChatInput {
    border-radius: 15px;
}

[data-testid="stStatusWidget"] {
    border: 1px solid #343444;
    border-radius: 12px;
}

[data-testid="stSidebar"] {
    background: #101018;
}

.stButton button {
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# CONFIGURATION
# ==================================================

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_SECRET_KEY"]

except KeyError as error:
    st.error(f"Missing required Streamlit Secret: {error}")
    st.stop()

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
OPENROUTER_API_KEY = st.secrets.get(
    "OPENROUTER_API_KEY", ""
)

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
        model.strip()
        for model in backup_config.split(",")
        if model.strip()
    ]
else:
    BACKUP_MODELS = list(backup_config)

GROQ_MODEL = st.secrets.get(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

OPENROUTER_MODEL = st.secrets.get(
    "OPENROUTER_MODEL",
    "openrouter/free"
)

MAX_CONTEXT_MESSAGES = 12
REQUEST_TIMEOUT = 90

SYSTEM_INSTRUCTION = """
You are FAHIM AI, an advanced professional AI assistant.

IDENTITY:
Your name is FAHIM AI.

CORE RESPONSIBILITIES:

1. Give accurate, useful and clear answers.
2. Understand Bengali and English.
3. Follow the language requested by the user.
4. Answer directly inside the chat.
5. Never invent facts, sources or links.
6. Explain uncertainty honestly.
7. Help with programming, AI, business,
   graphic design, writing and education.
8. When code is requested, provide complete,
   working and properly formatted code.
9. Use the available conversation history.
10. Avoid unnecessary introductions and repetition.
11. Explain technical instructions step by step.
12. Never claim to perform actions you did not perform.
13. Understand the user's actual question.
14. Do not invent missing personal information.
15. Do not claim live internet access unless
    a search tool is actually available.

PERSONAL PROFILE:
Use the user's available profile when relevant.

RESPONSE STYLE:
Be intelligent, professional, helpful and clear.
Provide detailed answers when requested.
Use appropriate formatting and examples.
"""

# ==================================================
# CLIENT CONNECTIONS
# ==================================================

@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)


@st.cache_resource(show_spinner=False)
def get_supabase_client(url, key):
    return create_client(url, key)


try:
    gemini_client = get_gemini_client(GEMINI_API_KEY)

    supabase = get_supabase_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

except Exception as error:
    st.error("Connection initialization failed.")
    st.exception(error)
    st.stop()


# ==================================================
# SESSION MANAGEMENT
# ==================================================

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


# ==================================================
# DATABASE - PERMANENT MEMORY
# ==================================================

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

        st.error("Message could not be saved.")
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

        st.error("Could not delete conversation.")
        st.code(str(error))

        return False


# ==================================================
# LOAD SAVED MEMORY
# ==================================================

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

if "last_error" not in st.session_state:
    st.session_state.last_error = None


# ==================================================
# ERROR CLASSIFICATION
# ==================================================

def is_quota_error(error):

    message = str(error).upper()

    return any(term in message for term in [
        "429",
        "RESOURCE_EXHAUSTED",
        "QUOTA_EXCEEDED",
        "RATE_LIMIT"
    ])


def is_auth_error(error):

    message = str(error).upper()

    return any(term in message for term in [
        "401",
        "403",
        "UNAUTHENTICATED",
        "PERMISSION_DENIED",
        "INVALID API KEY",
        "API_KEY_INVALID"
    ])


# ==================================================
# PREPARE CONVERSATION
# ==================================================

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


def prepare_openai_history(contents):

    messages = [{
        "role": "system",
        "content": SYSTEM_INSTRUCTION
    }]

    for item in contents:

        role = (
            "user"
            if item.role == "user"
            else "assistant"
        )

        text_content = "\n".join(
            part.text
            for part in item.parts
            if getattr(part, "text", None)
        )

        if text_content:

            messages.append({
                "role": role,
                "content": text_content
            })

    return messages


# ==================================================
# PROVIDER CONFIGURATION
# ==================================================

def get_providers():

    providers = [
        {
            "name": "Gemini Primary",
            "type": "gemini",
            "model": PRIMARY_MODEL
        }
    ]

    for model in BACKUP_MODELS:

        if model != PRIMARY_MODEL:

            providers.append({
                "name": "Gemini Backup",
                "type": "gemini",
                "model": model
            })

    if GROQ_API_KEY:

        providers.append({
            "name": "Groq",
            "type": "openai",
            "model": GROQ_MODEL,
            "key": GROQ_API_KEY,
            "url": "https://api.groq.com/openai/v1"
        })

    if OPENROUTER_API_KEY:

        providers.append({
            "name": "OpenRouter",
            "type": "openai",
            "model": OPENROUTER_MODEL,
            "key": OPENROUTER_API_KEY,
            "url": "https://openrouter.ai/api/v1"
        })

    return providers


# ==================================================
# GEMINI STREAMING
# ==================================================

def stream_gemini(model, contents, placeholder):

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION
    )

    stream = gemini_client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config
    )

    parts = []
    started = time.monotonic()
    last_status = started

    for chunk in stream:

        if time.monotonic() - started > REQUEST_TIMEOUT:
            raise TimeoutError("Gemini response timed out.")

        try:
            text = chunk.text
        except Exception:
            text = None

        if text:

            parts.append(text)

            placeholder.markdown(
                "".join(parts) + " ▌"
            )

        if time.monotonic() - last_status >= 3:
            last_status = time.monotonic()

    answer = "".join(parts)

    if not answer.strip():
        raise RuntimeError("Gemini returned an empty response.")

    return answer


# ==================================================
# GROQ / OPENROUTER STREAMING
# ==================================================

def stream_openai_compatible(provider, contents, placeholder):

    ai_client = OpenAI(
        api_key=provider["key"],
        base_url=provider["url"],
        timeout=REQUEST_TIMEOUT,
        max_retries=0
    )

    messages = prepare_openai_history(contents)

    stream = ai_client.chat.completions.create(
        model=provider["model"],
        messages=messages,
        stream=True,
        temperature=0.7
    )

    parts = []
    started = time.monotonic()

    for chunk in stream:

        if time.monotonic() - started > REQUEST_TIMEOUT:
            raise TimeoutError(
                f"{provider['name']} response timed out."
            )

        if not chunk.choices:
            continue

        text = chunk.choices[0].delta.content

        if text:

            parts.append(text)

            placeholder.markdown(
                "".join(parts) + " ▌"
            )

    answer = "".join(parts)

    if not answer.strip():
        raise RuntimeError(
            f"{provider['name']} returned an empty response."
        )

    return answer


# ==================================================
# HYBRID AI ROUTER
# ==================================================

def generate_answer(contents, placeholder, status):

    providers = get_providers()

    errors = []
    skip_remaining_gemini = False

    for index, provider in enumerate(providers):

        name = provider["name"]
        model = provider["model"]
        provider_type = provider["type"]

        if provider_type == "gemini" and skip_remaining_gemini:
            continue

        status.update(
            label=f"Connecting to {name}...",
            state="running",
            expanded=True
        )

        status.write(f"Model: {model}")
        status.write("Waiting for response...")

        placeholder.empty()

        try:

            if provider_type == "gemini":

                answer = stream_gemini(
                    model,
                    contents,
                    placeholder
                )

            else:

                answer = stream_openai_compatible(
                    provider,
                    contents,
                    placeholder
                )

            placeholder.markdown(answer)

            used_model = f"{name} | {model}"

            st.session_state.last_model = used_model
            st.session_state.last_error = None

            status.update(
                label=f"Completed successfully: {name}",
                state="complete",
                expanded=False
            )

            return answer, used_model

        except Exception as error:

            error_text = str(error)

            errors.append(
                f"{name} ({model}): {error_text}"
            )

            placeholder.empty()

            if (
                provider_type == "gemini"
                and is_quota_error(error)
            ):
                skip_remaining_gemini = True

            status.write(
                f"{name} failed. Checking next provider..."
            )

            if is_auth_error(error):
                status.write(
                    "Authentication error detected."
                )

            continue

    status.update(
        label="All AI providers failed.",
        state="error",
        expanded=True
    )

    raise RuntimeError(
        "No AI provider could generate a response:\n\n"
        + "\n\n".join(errors)
    )


# ==================================================
# HEADER
# ==================================================

st.title("🤖 FAHIM AI")

st.caption(
    "Hybrid AI Assistant | Gemini + Groq + OpenRouter | "
    "Permanent Memory"
)

st.divider()


# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:

    st.title("⚙️ Settings")

    st.success("Gemini connection configured")

    if GROQ_API_KEY:
        st.success("Groq configured")
    else:
        st.warning("Groq API key missing")

    if OPENROUTER_API_KEY:
        st.success("OpenRouter configured")
    else:
        st.warning("OpenRouter API key missing")

    st.success("Supabase configured")

    st.divider()

    st.write("**Primary Gemini model**")
    st.code(PRIMARY_MODEL)

    st.write("**Gemini backups**")

    for model in BACKUP_MODELS:
        st.caption(f"• {model}")

    st.divider()

    st.write("**Other AI providers**")

    if GROQ_API_KEY:
        st.caption(f"• Groq: {GROQ_MODEL}")

    if OPENROUTER_API_KEY:
        st.caption(f"• OpenRouter: {OPENROUTER_MODEL}")

    st.divider()

    st.metric(
        "Total messages",
        len(st.session_state.messages)
    )

    st.caption("Last successful model")

    st.code(st.session_state.last_model)

    st.metric(
        "Total requests",
        st.session_state.request_count
    )

    st.divider()

    if st.button(
        "🗑️ Clear conversation",
        use_container_width=True
    ):

        if delete_chat_history():

            st.session_state.messages = []
            st.session_state.last_error = None

            st.success("Conversation deleted.")
            st.rerun()

    st.divider()

    st.markdown("""
    ### FAHIM AI Features

    - Multi-provider AI engine
    - Gemini primary and backups
    - Groq fallback
    - OpenRouter fallback
    - Live text streaming
    - Automatic provider switching
    - Permanent chat history
    - Supabase database
    - Bengali and English
    - Programming assistance
    - Business assistance
    - Creative design assistance
    """)

    st.divider()

    st.caption("FAHIM GRAPHIC DESIGN")
    st.caption("Creative Design. Professional Results.")


# ==================================================
# DISPLAY CHAT HISTORY
# ==================================================

for message in st.session_state.messages:

    role = message["role"]

    if role not in ["user", "assistant"]:
        continue

    with st.chat_message(role):
        st.markdown(message["content"])


# ==================================================
# CHAT INPUT
# ==================================================

user_prompt = st.chat_input(
    "Ask Fahim AI anything..."
)


# ==================================================
# PROCESS USER MESSAGE
# ==================================================

if user_prompt:

    st.session_state.request_count += 1

    st.session_state.messages.append({
        "role": "user",
        "content": user_prompt
    })

    with st.chat_message("user"):
        st.markdown(user_prompt)

    user_saved = save_message(
        "user",
        user_prompt
    )

    if not user_saved:

        st.warning(
            "Message is visible in this session, "
            "but permanent saving failed."
        )

    api_history = prepare_history(
        st.session_state.messages
    )

    with st.chat_message("assistant"):

        placeholder = st.empty()

        try:

            with st.status(
                "FAHIM AI is starting...",
                expanded=True
            ) as status:

                answer, used_model = generate_answer(
                    api_history,
                    placeholder,
                    status
                )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

            assistant_saved = save_message(
                "assistant",
                answer
            )

            st.caption(f"⚡ Provider: {used_model}")

            if assistant_saved:

                st.caption(
                    "☁️ Permanently saved to Supabase"
                )

            else:

                st.warning(
                    "Answer generated, but permanent saving failed."
                )

        except Exception as error:

            st.session_state.last_error = str(error)

            placeholder.empty()

            st.error(
                "FAHIM AI could not complete the response."
            )

            with st.expander(
                "Technical error details",
                expanded=True
            ):

                st.code(str(error))

            st.info(
                "Check API keys, model availability, "
                "provider quota and internet connection."
            )


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "© 2026 FAHIM AI | Gemini + Groq + OpenRouter + Supabase"
)
