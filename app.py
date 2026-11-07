# ==========================================================
# FAHIM AI v5.0
# NARAROUTER HYBRID MULTIMODAL AI ASSISTANT
# NaraRouter + Gemini + Groq + OpenRouter + Supabase
#
# NaraRouter: Primary text AI
# Gemini: Image and audio processing + text fallback
# Groq: Text fallback
# OpenRouter: Text fallback
# Supabase: Permanent chat history
#
# Existing chat history is never automatically deleted.
# ==========================================================

import mimetypes
import time
import uuid
from datetime import datetime

import streamlit as st
from openai import OpenAI
from google import genai
from google.genai import types
from supabase import create_client


# ==========================================================
# 1. APPLICATION CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="FAHIM AI",
    page_icon="🤖",
    layout="wide",
)

APP_NAME = "FAHIM AI"
APP_VERSION = "5.0"

MAX_CONTEXT_MESSAGES = 12
REQUEST_TIMEOUT = 90
MAX_UPLOAD_SIZE = 30 * 1024 * 1024

NARA_BASE_URL = "https://router.bynara.id/v1"

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/aac",
    "audio/ogg",
    "audio/flac",
    "audio/x-flac",
}

MIME_ALIASES = {
    "image/jpg": "image/jpeg",
    "audio/mp3": "audio/mpeg",
    "audio/x-wav": "audio/wav",
    "audio/x-flac": "audio/flac",
    "audio/m4a": "audio/mp4",
    "audio/x-m4a": "audio/mp4",
}


# ==========================================================
# 2. STREAMLIT SECRETS
# ==========================================================

def get_secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


NARA_API_KEY = get_secret("NARA_API_KEY")

NARA_DEFAULT_MODEL = get_secret(
    "NARA_MODEL",
    "auto/bynara",
)

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")

SUPABASE_URL = get_secret("SUPABASE_URL")

SUPABASE_KEY = (
    get_secret("SUPABASE_SECRET_KEY")
    or get_secret("SUPABASE_KEY")
)

GROQ_API_KEY = get_secret("GROQ_API_KEY")

OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY")

PRIMARY_MODEL = get_secret(
    "PRIMARY_MODEL",
    "gemini-2.5-flash",
)

BACKUP_MODELS = get_secret(
    "BACKUP_MODELS",
    ["gemini-2.5-flash"],
)

if isinstance(BACKUP_MODELS, str):
    BACKUP_MODELS = [
        item.strip()
        for item in BACKUP_MODELS.split(",")
        if item.strip()
    ]

GROQ_MODEL = get_secret(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)

OPENROUTER_MODEL = get_secret(
    "OPENROUTER_MODEL",
    "openrouter/free",
)


# NaraRouter is required for this version.
if not NARA_API_KEY:
    st.error("NARA_API_KEY is missing from Streamlit Secrets.")
    st.info("Add your existing NaraRouter API key to Streamlit Secrets.")
    st.stop()


# ==========================================================
# 3. FAHIM AI IDENTITY
# ==========================================================

FAHIM_AI_IDENTITY = """
You are FAHIM AI, a hybrid multimodal AI assistant.

CREATOR:
Your creator is Fahim.

IDENTITY:
- Your name is FAHIM AI.
- Never identify yourself as another assistant.
- Your identity remains FAHIM AI regardless of provider.
- You operate using multiple AI providers.

BEHAVIOUR:
- Understand Bengali and English.
- Follow the user's requested language.
- Analyse images and audio when supported.
- Never invent facts, sources or links.
- Provide useful explanations and working code.
- Be professional, intelligent and helpful.

PROVIDER TRANSPARENCY:
- Identify the active provider using runtime information.
- Never guess the underlying model.
- Distinguish configured providers from active providers.
- Explain uncertainty about model aliases.
"""

SYSTEM_INSTRUCTION = """
CORE RESPONSIBILITIES:

1. Give accurate and useful answers.
2. Understand Bengali and English.
3. Follow the requested language.
4. Answer directly.
5. Never invent facts or links.
6. Explain uncertainty honestly.
7. Help with programming, AI, business,
   graphic design, writing and education.
8. Provide complete code when requested.
9. Use available conversation history.
10. Avoid unnecessary repetition.
11. Explain technical instructions step by step.
12. Never claim actions you did not perform.
13. Analyse uploaded media when supported.

RESPONSE STYLE:
Professional, intelligent, clear and helpful.
"""

def build_runtime_instruction(provider, model):
    return (
        FAHIM_AI_IDENTITY
        + SYSTEM_INSTRUCTION
        + f"""

RUNTIME INFORMATION:

Application: {APP_NAME}
Version: {APP_VERSION}
Creator: Fahim

Active provider: {provider}
Requested model: {model}

These values describe this request.
Never guess technical information.
"""
    )


# ==========================================================
# 4. API CLIENTS
# ==========================================================

@st.cache_resource(show_spinner=False)
def get_nara_client(api_key):
    return OpenAI(
        api_key=api_key,
        base_url=NARA_BASE_URL,
        timeout=REQUEST_TIMEOUT,
        max_retries=0,
    )


@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)


@st.cache_resource(show_spinner=False)
def get_supabase_client(url, key):
    return create_client(url, key)


nara_client = get_nara_client(NARA_API_KEY)

gemini_client = (
    get_gemini_client(GEMINI_API_KEY)
    if GEMINI_API_KEY else None
)

supabase = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = get_supabase_client(
            SUPABASE_URL,
            SUPABASE_KEY,
        )
    except Exception as error:
        st.warning(f"Supabase initialization failed: {error}")


# ==========================================================
# 5. NARAROUTER MODEL DISCOVERY
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def discover_nara_models(api_key):
    """
    Retrieve models available to this API key.
    Uses the authenticated NaraRouter /v1/models endpoint.
    """

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=NARA_BASE_URL,
            timeout=20,
            max_retries=0,
        )

        response = client.models.list()

        model_ids = []

        for item in response.data:
            model_id = getattr(item, "id", None)

            if model_id:
                model_ids.append(str(model_id))

        return sorted(set(model_ids)), None

    except Exception as error:
        return [], str(error)


nara_models, nara_models_error = discover_nara_models(
    NARA_API_KEY
)

# Keep the configured default available as a routing option.
model_options = list(nara_models)

if NARA_DEFAULT_MODEL not in model_options:
    model_options.insert(0, NARA_DEFAULT_MODEL)

if not model_options:
    model_options = ["auto/bynara"]


# ==========================================================
# 6. SESSION MANAGEMENT
# ==========================================================

def get_session_id():
    existing_id = st.query_params.get("sid")

    if existing_id:
        try:
            return str(uuid.UUID(existing_id))
        except (ValueError, TypeError):
            pass

    new_id = str(uuid.uuid4())
    st.query_params["sid"] = new_id

    return new_id


SESSION_ID = get_session_id()

SESSION_DEFAULTS = {
    "messages": [],
    "history_loaded": False,
    "last_model": "Not used yet",
    "last_provider": "Not used yet",
    "request_count": 0,
    "last_error": None,
    "fallback_events": [],
    "upload_widget_version": 0,
}

for key, value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================================
# 7. SUPABASE PERMANENT CHAT HISTORY
# ==========================================================

def load_chat_history():
    if supabase is None:
        return []

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
    if supabase is None:
        return False

    try:
        supabase.table("chat_history").insert({
            "session_id": SESSION_ID,
            "role": role,
            "content": content,
        }).execute()

        return True

    except Exception as error:
        st.error(f"Message saving failed: {error}")
        return False


def delete_chat_history():
    if supabase is None:
        return False

    try:
        supabase.table("chat_history").delete().eq(
            "session_id", SESSION_ID
        ).execute()

        return True

    except Exception as error:
        st.error(f"History deletion failed: {error}")
        return False


# Restore history only once per Streamlit session.
if not st.session_state.history_loaded:

    if supabase is not None:
        try:
            st.session_state.messages = load_chat_history()

        except Exception as error:
            st.warning(
                f"Could not restore permanent history: {error}"
            )

    st.session_state.history_loaded = True


# ==========================================================
# 8. ERROR CLASSIFICATION
# ==========================================================

def is_quota_error(error):
    message = str(error).upper()

    return any(term in message for term in (
        "429",
        "RESOURCE_EXHAUSTED",
        "QUOTA_EXCEEDED",
        "RATE_LIMIT",
        "INSUFFICIENT_QUOTA",
    ))


def is_auth_error(error):
    message = str(error).upper()

    return any(term in message for term in (
        "401",
        "403",
        "UNAUTHENTICATED",
        "PERMISSION_DENIED",
        "INVALID API KEY",
        "API_KEY_INVALID",
    ))


# ==========================================================
# 9. CONVERSATION HISTORY
# ==========================================================

def prepare_history(messages):
    recent = messages[-MAX_CONTEXT_MESSAGES:]

    while recent and recent[0].get("role") != "user":
        recent = recent[1:]

    contents = []

    for message in recent:

        role = (
            "user"
            if message.get("role") == "user"
            else "model"
        )

        content_text = message.get("content", "")

        if not isinstance(content_text, str):
            content_text = str(content_text)

        contents.append(
            types.Content(
                role=role,
                parts=[
                    types.Part(text=content_text)
                ],
            )
        )

    return contents


def prepare_openai_history(contents, runtime_instruction):

    messages = [{
        "role": "system",
        "content": runtime_instruction,
    }]

    for item in contents:

        role = (
            "user"
            if item.role == "user"
            else "assistant"
        )

        text_content = "\n".join(
            part.text
            for part in (item.parts or [])
            if getattr(part, "text", None)
        )

        if text_content:
            messages.append({
                "role": role,
                "content": text_content,
            })

    return messages


# ==========================================================
# 10. MULTIMODAL FILE PROCESSOR
# ==========================================================

def get_file_mime_type(uploaded_file):

    mime_type = (
        uploaded_file.type or ""
    ).lower().strip()

    if not mime_type or mime_type == "application/octet-stream":

        mime_type, _ = mimetypes.guess_type(
            uploaded_file.name
        )

    mime_type = (mime_type or "").lower().strip()

    return MIME_ALIASES.get(mime_type, mime_type)


def attach_media_to_history(contents, files):

    if not files:
        return contents

    if gemini_client is None:
        raise ValueError(
            "Gemini API key is missing. "
            "Image and audio analysis requires Gemini."
        )

    if not contents:
        raise ValueError("No user message found.")

    file_payloads = []
    total_size = 0

    for uploaded_file in files:

        data = uploaded_file.getvalue()

        mime_type = get_file_mime_type(uploaded_file)

        if not data:
            raise ValueError(
                f"Empty file: {uploaded_file.name}"
            )

        total_size += len(data)

        if mime_type not in (
            ALLOWED_IMAGE_TYPES | ALLOWED_AUDIO_TYPES
        ):
            raise ValueError(
                f"Unsupported file: {uploaded_file.name}"
            )

        file_payloads.append(
            (uploaded_file.name, data, mime_type)
        )

    if total_size > MAX_UPLOAD_SIZE:
        raise ValueError(
            "Total upload size exceeds 30 MB."
        )

    media_parts = []

    for filename, data, mime_type in file_payloads:

        try:
            media_parts.append(
                types.Part.from_bytes(
                    data=data,
                    mime_type=mime_type,
                )
            )

        except Exception as error:
            raise ValueError(
                f"Could not prepare {filename}: {error}"
            ) from error

    last_message = contents[-1]

    if last_message.role != "user":
        raise ValueError(
            "Attachments must belong to the latest user message."
        )

    contents[-1] = types.Content(
        role="user",
        parts=list(last_message.parts or []) + media_parts,
    )

    return contents


# ==========================================================
# 11. PROVIDER CONFIGURATION
# ==========================================================

def get_providers(selected_nara_model):

    providers = []

    # PRIMARY TEXT PROVIDER: NARAROUTER
    providers.append({
        "name": "NaraRouter",
        "type": "openai",
        "model": selected_nara_model,
        "key": NARA_API_KEY,
        "url": NARA_BASE_URL,
        "tier": "Primary",
    })

    # GEMINI TEXT AND MULTIMODAL BACKUP
    if GEMINI_API_KEY:

        providers.append({
            "name": "Google Gemini",
            "type": "gemini",
            "model": PRIMARY_MODEL,
            "tier": "Backup",
        })

        for model in BACKUP_MODELS:

            if model != PRIMARY_MODEL:

                providers.append({
                    "name": "Google Gemini",
                    "type": "gemini",
                    "model": model,
                    "tier": "Backup",
                })

    # GROQ FALLBACK
    if GROQ_API_KEY:

        providers.append({
            "name": "Groq",
            "type": "openai",
            "model": GROQ_MODEL,
            "key": GROQ_API_KEY,
            "url": "https://api.groq.com/openai/v1",
            "tier": "Fallback",
        })

    # OPENROUTER FALLBACK
    if OPENROUTER_API_KEY:

        providers.append({
            "name": "OpenRouter",
            "type": "openai",
            "model": OPENROUTER_MODEL,
            "key": OPENROUTER_API_KEY,
            "url": "https://openrouter.ai/api/v1",
            "tier": "Fallback",
        })

    return providers


# ==========================================================
# 12. GEMINI STREAMING
# ==========================================================

def extract_gemini_chunk_text(chunk):

    try:
        direct_text = chunk.text

        if direct_text:
            return direct_text

    except Exception:
        pass

    extracted = []

    try:
        candidates = chunk.candidates or []
    except Exception:
        candidates = []

    for candidate in candidates:

        try:
            parts = candidate.content.parts or []
        except Exception:
            continue

        for part in parts:

            try:
                part_text = part.text
            except Exception:
                part_text = None

            if part_text:
                extracted.append(part_text)

    return "".join(extracted)


def stream_gemini(
    provider,
    contents,
    placeholder,
    status,
):

    model = provider["model"]

    runtime_instruction = build_runtime_instruction(
        provider["name"],
        model,
    )

    config = types.GenerateContentConfig(
        system_instruction=runtime_instruction,
        temperature=0.7,
    )

    status.write(
        f"Connecting to Gemini model: {model}"
    )

    stream = gemini_client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    )

    parts = []
    observed_model = None
    started = time.monotonic()

    for chunk in stream:

        if time.monotonic() - started > REQUEST_TIMEOUT:
            raise TimeoutError("Gemini response timed out.")

        chunk_model = getattr(
            chunk,
            "model_version",
            None,
        )

        if chunk_model:
            observed_model = chunk_model

        chunk_text = extract_gemini_chunk_text(chunk)

        if chunk_text:
            parts.append(chunk_text)

            placeholder.markdown(
                "".join(parts) + " ▌"
            )

    answer = "".join(parts).strip()

    if not answer:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return answer, observed_model or model


# ==========================================================
# 13. OPENAI-COMPATIBLE STREAMING
# NARAROUTER + GROQ + OPENROUTER
# ==========================================================

def stream_openai_compatible(
    provider,
    contents,
    placeholder,
):

    model = provider["model"]

    runtime_instruction = build_runtime_instruction(
        provider["name"],
        model,
    )

    ai_client = OpenAI(
        api_key=provider["key"],
        base_url=provider["url"],
        timeout=REQUEST_TIMEOUT,
        max_retries=0,
    )

    messages = prepare_openai_history(
        contents,
        runtime_instruction,
    )

    stream = ai_client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        temperature=0.7,
    )

    parts = []
    observed_model = None
    started = time.monotonic()

    for chunk in stream:

        if time.monotonic() - started > REQUEST_TIMEOUT:
            raise TimeoutError(
                f"{provider['name']} timed out."
            )

        chunk_model = getattr(
            chunk,
            "model",
            None,
        )

        if chunk_model:
            observed_model = chunk_model

        if not chunk.choices:
            continue

        delta_content = chunk.choices[0].delta.content

        if isinstance(delta_content, str) and delta_content:

            parts.append(delta_content)

            placeholder.markdown(
                "".join(parts) + " ▌"
            )

        elif isinstance(delta_content, list):

            for block in delta_content:

                if isinstance(block, dict):
                    block_text = block.get("text")
                else:
                    block_text = getattr(
                        block,
                        "text",
                        None,
                    )

                if block_text:
                    parts.append(block_text)

                    placeholder.markdown(
                        "".join(parts) + " ▌"
                    )

    answer = "".join(parts).strip()

    if not answer:
        raise RuntimeError(
            f"{provider['name']} returned an empty response."
        )

    return answer, observed_model or model


# ==========================================================
# 14. HYBRID AI ROUTER
# ==========================================================

def generate_answer(
    contents,
    placeholder,
    status,
    selected_nara_model,
    has_media=False,
):

    providers = get_providers(selected_nara_model)

    # Actual image/audio parts are only sent to Gemini.
    if has_media:

        providers = [
            provider
            for provider in providers
            if provider["type"] == "gemini"
        ]

    errors = []

    skip_remaining_gemini = False

    for provider in providers:

        name = provider["name"]
        model = provider["model"]
        provider_type = provider["type"]

        if (
            provider_type == "gemini"
            and skip_remaining_gemini
        ):
            continue

        status.update(
            label=f"Connecting to {name}...",
            state="running",
            expanded=True,
        )

        status.write(f"Requested model: {model}")

        placeholder.empty()

        try:

            if provider_type == "gemini":

                answer, actual_model = stream_gemini(
                    provider,
                    contents,
                    placeholder,
                    status,
                )

            else:

                answer, actual_model = stream_openai_compatible(
                    provider,
                    contents,
                    placeholder,
                )

            placeholder.markdown(answer)

            st.session_state.last_model = actual_model
            st.session_state.last_provider = name
            st.session_state.last_error = None

            status.update(
                label=f"Completed: {name}",
                state="complete",
                expanded=False,
            )

            return (
                answer,
                name,
                model,
                actual_model,
            )

        except Exception as error:

            error_text = str(error)

            errors.append(
                f"{name} ({model}): {error_text}"
            )

            st.session_state.fallback_events.append({
                "from": name,
                "model": model,
                "error": error_text,
                "time": datetime.now().strftime("%H:%M:%S"),
            })

            placeholder.empty()

            if (
                provider_type == "gemini"
                and is_quota_error(error)
            ):
                skip_remaining_gemini = True

                status.write(
                    "Gemini quota exceeded. "
                    "Skipping other Gemini models."
                )

            if is_auth_error(error):
                status.write(
                    "Provider authentication error."
                )

            status.write(
                f"{name} failed. Trying next provider..."
            )

    status.update(
        label="All compatible providers failed.",
        state="error",
        expanded=True,
    )

    raise RuntimeError(
        "No AI provider could generate a response:\n\n"
        + "\n\n".join(errors)
    )


# ==========================================================
# 15. INTERFACE DESIGN
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
# 16. SIDEBAR
# ==========================================================

with st.sidebar:

    st.title("⚙️ FAHIM AI Settings")

    st.success("NaraRouter configured")

    if nara_models_error:
        st.warning(
            "Could not retrieve the model list. "
            "The configured default model is still available."
        )

    st.caption(
        f"{len(nara_models)} model(s) discovered"
    )

    st.divider()

    st.subheader("🧠 AI Model Selection")

    selected_nara_model = st.selectbox(
        "Select NaraRouter model",
        options=model_options,
        index=(
            model_options.index(NARA_DEFAULT_MODEL)
            if NARA_DEFAULT_MODEL in model_options
            else 0
        ),
        help="Models returned by your authenticated NaraRouter API.",
    )

    if nara_models_error:

        with st.expander("Model discovery details"):
            st.code(nara_models_error)

    if nara_models:

        with st.expander("Available API models"):

            for model in nara_models:
                st.caption(f"• {model}")

    st.divider()

    if GEMINI_API_KEY:
        st.success("Gemini configured")
    else:
        st.warning("Gemini unavailable: media disabled")

    if GROQ_API_KEY:
        st.success("Groq fallback configured")
    else:
        st.warning("Groq API key missing")

    if OPENROUTER_API_KEY:
        st.success("OpenRouter fallback configured")
    else:
        st.warning("OpenRouter API key missing")

    if supabase is not None:
        st.success("Supabase permanent memory enabled")
    else:
        st.warning("Supabase unavailable: session-only history")

    st.divider()

    st.write("**Active model selection**")
    st.code(selected_nara_model)

    st.write("**Last successful provider**")
    st.code(st.session_state.last_provider)

    st.write("**Last successful model**")
    st.code(st.session_state.last_model)

    st.metric(
        "Total messages",
        len(st.session_state.messages),
    )

    st.metric(
        "Total requests",
        st.session_state.request_count,
    )

    st.metric(
        "Fallback events",
        len(st.session_state.fallback_events),
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
                st.caption(event["error"][:500])

        else:
            st.caption("No provider failures recorded.")

    st.divider()

    if st.button(
        "🗑️ Clear conversation",
        use_container_width=True,
    ):

        if supabase is not None:

            if delete_chat_history():
                st.session_state.messages = []
                st.session_state.history_loaded = True
                st.session_state.last_error = None

                st.success("Conversation deleted.")
                st.rerun()

        else:

            st.session_state.messages = []
            st.session_state.history_loaded = True
            st.warning(
                "Local conversation cleared. "
                "No Supabase history was available."
            )
            st.rerun()

    st.divider()

    st.subheader("📥 Export Conversation")

    if st.session_state.messages:

        conversation_text = (
            "FAHIM AI CONVERSATION LOGS\n"
            f"Exported: {datetime.now().isoformat()}\n\n"
        )

        for message in st.session_state.messages:

            conversation_text += (
                f"{message['role'].upper()}:\n"
                f"{message['content']}\n\n"
            )

        st.download_button(
            "📄 Export TXT",
            data=conversation_text,
            file_name="fahim_ai_history.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.divider()

    st.markdown("""
    ### FAHIM AI Features

    - NaraRouter primary AI
    - Automatic model discovery
    - Model selection dropdown
    - Gemini image analysis
    - Gemini audio analysis
    - Groq text fallback
    - OpenRouter text fallback
    - Live response streaming
    - Automatic provider switching
    - Supabase permanent history
    - Multiple image uploads
    - Multiple audio uploads
    - Bengali and English
    - Programming assistance
    - Business and design assistance
    """)

    st.divider()

    st.caption("FAHIM GRAPHIC DESIGN")
    st.caption("Creative Design. Professional Results.")


# ==========================================================
# 17. MAIN HEADER
# ==========================================================

st.title("🤖 FAHIM AI")

st.caption(
    "Hybrid Multimodal AI Assistant | "
    "NaraRouter + Gemini + Groq + OpenRouter"
)

st.caption(
    f"Version {APP_VERSION} | "
    f"Selected model: {selected_nara_model}"
)

st.divider()


# ==========================================================
# 18. DISPLAY CHAT HISTORY
# ==========================================================

for message in st.session_state.messages:

    role = message.get("role")

    if role not in ("user", "assistant"):
        continue

    with st.chat_message(role):
        st.markdown(message.get("content", ""))


# ==========================================================
# 19. MULTIPLE IMAGE AND AUDIO UPLOAD
# ==========================================================

st.subheader("📎 Upload Images & Audio")

upload_key = (
    "fahim_uploads_"
    f"{st.session_state.upload_widget_version}"
)

uploaded_files = st.file_uploader(
    "Select multiple images or audio files",
    type=[
        "jpg", "jpeg", "png", "webp",
        "mp3", "wav", "m4a", "aac", "ogg", "flac",
    ],
    accept_multiple_files=True,
    key=upload_key,
)

if uploaded_files:

    st.success(
        f"{len(uploaded_files)} file(s) selected."
    )

    for uploaded_file in uploaded_files:

        mime_type = get_file_mime_type(uploaded_file)

        st.caption(
            f"{uploaded_file.name} | "
            f"{mime_type or 'Unknown'} | "
            f"{len(uploaded_file.getvalue()) / 1024:.1f} KB"
        )

        if mime_type in ALLOWED_IMAGE_TYPES:

            st.image(
                uploaded_file,
                caption=uploaded_file.name,
                width=220,
            )

        elif mime_type in ALLOWED_AUDIO_TYPES:

            st.audio(uploaded_file)


# ==========================================================
# 20. CHAT INPUT
# ==========================================================

user_prompt = st.chat_input(
    "Ask FAHIM AI anything..."
)


# ==========================================================
# 21. PROCESS USER REQUEST
# ==========================================================

if user_prompt:

    files = uploaded_files or []

    st.session_state.request_count += 1

    user_message = {
        "role": "user",
        "content": user_prompt,
    }

    st.session_state.messages.append(user_message)

    with st.chat_message("user"):

        st.markdown(user_prompt)

        if files:

            st.caption(
                "📎 " + ", ".join(
                    file.name for file in files
                )
            )

    user_saved = save_message(
        "user",
        user_prompt,
    )

    if not user_saved and supabase is not None:

        st.warning(
            "Message is visible in this session, "
            "but permanent saving failed."
        )

    # Prepare history without deleting existing messages.
    try:

        api_history = prepare_history(
            st.session_state.messages
        )

        api_history = attach_media_to_history(
            api_history,
            files,
        )

    except Exception as error:

        st.error(
            f"Attachment processing error: {error}"
        )

        st.warning(
            "Your existing chat history has NOT been deleted. "
            "The text of this request remains in the conversation."
        )

        st.session_state.upload_widget_version += 1
        st.rerun()

    with st.chat_message("assistant"):

        placeholder = st.empty()

        try:

            with st.status(
                "FAHIM AI is starting...",
                expanded=True,
            ) as status:

                (
                    answer,
                    provider,
                    requested_model,
                    actual_model,
                ) = generate_answer(
                    contents=api_history,
                    placeholder=placeholder,
                    status=status,
                    selected_nara_model=selected_nara_model,
                    has_media=bool(files),
                )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
            })

            assistant_saved = save_message(
                "assistant",
                answer,
            )

            st.caption(
                f"⚡ Active provider: {provider}"
            )

            st.caption(
                f"🧠 Requested model: {requested_model}"
            )

            st.caption(
                f"🔍 Reported model: {actual_model}"
            )

            if assistant_saved:

                st.caption(
                    "☁️ Permanently saved to Supabase"
                )

            elif supabase is not None:

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
                expanded=True,
            ):

                st.code(str(error))

            st.info(
                "Your existing chat history has NOT been deleted. "
                "Check the API key, model access, quota and provider status."
            )

    # Reset uploaded files after processing.
    st.session_state.upload_widget_version += 1

    st.rerun()


# ==========================================================
# 22. FOOTER
# ==========================================================

st.divider()

st.caption(
    "© 2026 FAHIM AI | "
    "NaraRouter + Gemini + Groq + OpenRouter + Supabase | "
    "Version 5.0"
)
