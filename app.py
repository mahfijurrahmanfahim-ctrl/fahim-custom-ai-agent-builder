
# ==========================================================
# FAHIM AI — HYBRID MULTI-PROVIDER AI ASSISTANT
# Gemini + Groq + OpenRouter + Supabase
# Runtime Identity + Provider Detection + Permanent Memory
# ==========================================================

import streamlit as st
import os
import json
import time
import uuid

from datetime import datetime
from google import genai
from google.genai import types
from supabase import create_client
from openai import OpenAI


# ==========================================================
# 1. APPLICATION CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="FAHIM AI",
    page_icon="🤖",
    layout="wide"
)

APP_NAME = "FAHIM AI"
APP_VERSION = "3.0"

MAX_CONTEXT_MESSAGES = 12
REQUEST_TIMEOUT = 90


# ==========================================================
# 2. FAHIM AI PERMANENT IDENTITY
# ==========================================================

FAHIM_AI_IDENTITY = """
You are FAHIM AI, an advanced hybrid AI assistant.

CREATOR:
Your creator is Fahim.

IDENTITY:
- Your name is FAHIM AI.
- Never identify yourself as Flint or Recursive.
- You are configured to work with multiple AI providers.
- Your identity remains FAHIM AI regardless of which
  underlying AI model answers.

PROVIDER TRANSPARENCY:
- Use the runtime provider information supplied by
  the application.
- Identify the actual active provider.
- Identify the configured/requested model.
- Never invent provider or model information.
- Distinguish configured providers from active providers.
- If the exact underlying model is unavailable, explain that.

BEHAVIOUR:
- Answer accurately and intelligently.
- Understand Bengali and English.
- Follow the user's requested language.
- Use available personal profile information.
- Never invent personal information.
- Provide useful explanations and working code.
- Be professional, conversational and helpful.
"""


SYSTEM_INSTRUCTION = """
You are FAHIM AI.

Your creator is Fahim.

CORE RESPONSIBILITIES:

1. Give accurate, useful and clear answers.
2. Understand Bengali and English.
3. Follow the language requested by the user.
4. Answer directly inside the chat.
5. Never invent facts, sources or links.
6. Explain uncertainty honestly.
7. Help with programming, AI, business,
   graphic design, writing and education.
8. Provide complete working code when requested.
9. Use available conversation history.
10. Avoid unnecessary introductions and repetition.
11. Explain technical instructions step by step.
12. Never claim actions you did not perform.
13. Do not invent missing personal information.
14. Never claim live internet access unless available.

PERSONAL PROFILE:
Use available user profile information when relevant.

RESPONSE STYLE:
Be intelligent, professional, helpful and clear.
Provide detailed answers when requested.
Use appropriate formatting and examples.
"""


# ==========================================================
# 3. RUNTIME IDENTITY
# ==========================================================

def build_runtime_instruction(provider, model):

    return FAHIM_AI_IDENTITY + SYSTEM_INSTRUCTION + f"""

CURRENT REQUEST RUNTIME INFORMATION:

Application: {APP_NAME}
Creator: Fahim

ACTIVE PROVIDER:
{provider}

ACTIVE REQUESTED MODEL:
{model}

IMPORTANT:
These values are supplied by the application.
They describe the provider and model selected for this
specific request, not every configured provider.

Never claim another provider answered this request.
Never guess the actual underlying model.
If the provider uses a dynamic model alias, explain that.
"""


# ==========================================================
# 4. SECRETS AND API CONFIGURATION
# ==========================================================

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


# ==========================================================
# 5. CLIENT CONNECTIONS
# ==========================================================

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


# ==========================================================
# 6. SESSION MANAGEMENT
# ==========================================================

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


if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_model" not in st.session_state:
    st.session_state.last_model = "Not used yet"

if "last_provider" not in st.session_state:
    st.session_state.last_provider = "Not used yet"

if "request_count" not in st.session_state:
    st.session_state.request_count = 0

if "last_error" not in st.session_state:
    st.session_state.last_error = None

if "fallback_events" not in st.session_state:
    st.session_state.fallback_events = []


# ==========================================================
# 7. SUPABASE PERMANENT CHAT MEMORY
# ==========================================================

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


# Restore permanent history

if not st.session_state.messages:

    try:

        st.session_state.messages = load_chat_history()

    except Exception as error:

        st.error("Could not restore permanent chat history.")
        st.exception(error)
        st.stop()


# ==========================================================
# 8. ERROR CLASSIFICATION
# ==========================================================

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


# ==========================================================
# 9. PREPARE CONVERSATION HISTORY
# ==========================================================

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


def prepare_openai_history(contents, runtime_instruction):

    messages = [{
        "role": "system",
        "content": runtime_instruction
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


# ==========================================================
# 10. PROVIDER CONFIGURATION
# ==========================================================

def get_providers():

    providers = [
        {
            "name": "Google Gemini",
            "type": "gemini",
            "model": PRIMARY_MODEL,
            "tier": "Primary"
        }
    ]

    for model in BACKUP_MODELS:

        if model != PRIMARY_MODEL:

            providers.append({
                "name": "Google Gemini",
                "type": "gemini",
                "model": model,
                "tier": "Backup"
            })

    if GROQ_API_KEY:

        providers.append({
            "name": "Groq",
            "type": "openai",
            "model": GROQ_MODEL,
            "key": GROQ_API_KEY,
            "url": "https://api.groq.com/openai/v1",
            "tier": "Fallback"
        })

    if OPENROUTER_API_KEY:

        providers.append({
            "name": "OpenRouter",
            "type": "openai",
            "model": OPENROUTER_MODEL,
            "key": OPENROUTER_API_KEY,
            "url": "https://openrouter.ai/api/v1",
            "tier": "Fallback"
        })

    return providers


# ==========================================================
# 11. GEMINI LIVE STREAMING
# ==========================================================

def stream_gemini(
    provider,
    contents,
    placeholder
):

    model = provider["model"]

    runtime_instruction = build_runtime_instruction(
        provider["name"],
        model
    )

    config = types.GenerateContentConfig(
        system_instruction=runtime_instruction
    )

    stream = gemini_client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config
    )

    parts = []
    observed_model = None
    started = time.monotonic()

    for chunk in stream:

        if time.monotonic() - started > REQUEST_TIMEOUT:
            raise TimeoutError("Gemini response timed out.")

        chunk_model = getattr(chunk, "model_version", None)

        if chunk_model:
            observed_model = chunk_model

        try:
            text = chunk.text
        except Exception:
            text = None

        if text:

            parts.append(text)

            placeholder.markdown(
                "".join(parts) + " ▌"
            )

    answer = "".join(parts)

    if not answer.strip():
        raise RuntimeError("Gemini returned an empty response.")

    return answer, observed_model or model


# ==========================================================
# 12. GROQ / OPENROUTER STREAMING
# ==========================================================

def stream_openai_compatible(
    provider,
    contents,
    placeholder
):

    model = provider["model"]

    runtime_instruction = build_runtime_instruction(
        provider["name"],
        model
    )

    ai_client = OpenAI(
        api_key=provider["key"],
        base_url=provider["url"],
        timeout=REQUEST_TIMEOUT,
        max_retries=0
    )

    messages = prepare_openai_history(
        contents,
        runtime_instruction
    )

    stream = ai_client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        temperature=0.7
    )

    parts = []
    observed_model = None
    started = time.monotonic()

    for chunk in stream:

        if time.monotonic() - started > REQUEST_TIMEOUT:
            raise TimeoutError(
                f"{provider['name']} response timed out."
            )

        chunk_model = getattr(chunk, "model", None)

        if chunk_model:
            observed_model = chunk_model

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

    return answer, observed_model or model


# ==========================================================
# 13. HYBRID AI ROUTER
# ==========================================================

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

        status.write(f"Requested model: {model}")
        status.write("Sending runtime identity information...")
        status.write("Waiting for AI response...")

        placeholder.empty()

        try:

            if provider_type == "gemini":

                answer, actual_model = stream_gemini(
                    provider,
                    contents,
                    placeholder
                )

            else:

                answer, actual_model = stream_openai_compatible(
                    provider,
                    contents,
                    placeholder
                )

            placeholder.markdown(answer)

            used_model = f"{name} | {actual_model}"

            st.session_state.last_model = actual_model
            st.session_state.last_provider = name
            st.session_state.last_error = None

            status.update(
                label=f"Completed successfully: {name}",
                state="complete",
                expanded=False
            )

            return answer, name, model, actual_model

        except Exception as error:

            error_text = str(error)

            errors.append(
                f"{name} ({model}): {error_text}"
            )

            fallback_record = {
                "from": name,
                "model": model,
                "error": error_text,
                "time": datetime.now().strftime("%H:%M:%S")
            }

            st.session_state.fallback_events.append(
                fallback_record
            )

            placeholder.empty()

            if (
                provider_type == "gemini"
                and is_quota_error(error)
            ):
                skip_remaining_gemini = True

                status.write(
                    "Gemini quota issue. Skipping remaining "
                    "Gemini models."
                )

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


# ==========================================================
# 14. USER INTERFACE DESIGN
# ==========================================================

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


# ==========================================================
# 15. SIDEBAR SETTINGS
# ==========================================================

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

    st.write("**Last successful provider**")
    st.code(st.session_state.last_provider)

    st.write("**Last successful model**")
    st.code(st.session_state.last_model)

    st.metric(
        "Total messages",
        len(st.session_state.messages)
    )

    st.metric(
        "Total requests",
        st.session_state.request_count
    )

    st.metric(
        "Fallback events",
        len(st.session_state.fallback_events)
    )

    with st.expander("Provider fallback history"):

        if st.session_state.fallback_events:

            for event in reversed(
                st.session_state.fallback_events[-10:]
            ):

                st.write(
                    f"**{event['from']}** — {event['model']}"
                )

                st.caption(event["time"])
                st.caption(event["error"][:250])

        else:

            st.caption("No provider failures recorded.")

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

    - Hybrid multi-provider AI
    - Gemini primary and backups
    - Groq fallback
    - OpenRouter fallback
    - Runtime provider detection
    - Runtime model identification
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


# ==========================================================
# 16. HEADER
# ==========================================================

st.title("🤖 FAHIM AI")

st.caption(
    "Hybrid AI Assistant | Gemini + Groq + OpenRouter | "
    "Permanent Memory"
)

st.divider()


# ==========================================================
# 17. DISPLAY CHAT HISTORY
# ==========================================================

for message in st.session_state.messages:

    role = message["role"]

    if role not in ["user", "assistant"]:
        continue

    with st.chat_message(role):
        st.markdown(message["content"])


# ==========================================================
# 18. CHAT INPUT
# ==========================================================

user_prompt = st.chat_input(
    "Ask Fahim AI anything..."
)


# ==========================================================
# 19. PROCESS USER MESSAGE
# ==========================================================

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

                answer, provider, requested_model, actual_model = (
                    generate_answer(
                        api_history,
                        placeholder,
                        status
                    )
                )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

            assistant_saved = save_message(
                "assistant",
                answer
            )

            st.caption(
                f"⚡ Active provider: {provider}"
            )

            st.caption(
                f"🧠 Requested model: {requested_model}"
            )

            st.caption(
                f"🔍 Reported response model: {actual_model}"
            )

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


# ==========================================================
# 20. FOOTER
# ==========================================================

st.divider()

st.caption(
    "© 2026 FAHIM AI | Gemini + Groq + OpenRouter + Supabase"
)
