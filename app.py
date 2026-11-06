# ==========================================================
# FAHIM AI v4.1
# HYBRID MULTI-PROVIDER MULTIMODAL AI ASSISTANT
# Gemini + Groq + OpenRouter + Supabase
# Multiple Images + Multiple Audio Files
# Permanent Text Chat History + Runtime Provider Detection
#
# IMPORTANT:
# - Media requests are sent to Gemini only (image/audio capable).
# - OpenAI-compatible text providers are never given fake text-only
#   representations of uploaded media.
# - Attachment errors NEVER delete existing chat history.
# - Supabase stores chat text; uploaded media is processed per request.
# ==========================================================

import mimetypes
import time
import uuid
from datetime import datetime

import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI
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
APP_VERSION = "4.1"

MAX_CONTEXT_MESSAGES = 12
REQUEST_TIMEOUT = 90
MAX_UPLOAD_SIZE = 30 * 1024 * 1024

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
# 2. FAHIM AI IDENTITY
# ==========================================================

FAHIM_AI_IDENTITY = """
You are FAHIM AI, an advanced hybrid AI assistant.

CREATOR:
Your creator is Fahim.

IDENTITY:
- Your name is FAHIM AI.
- Never identify yourself as another assistant.
- Your identity remains FAHIM AI regardless of provider.
- You operate using multiple configured AI providers.

PROVIDER TRANSPARENCY:
- Use application-supplied runtime information.
- Identify the active provider accurately.
- Distinguish configured providers from active providers.
- Never invent the underlying model.
- Explain when a dynamic model alias is being used.

BEHAVIOUR:
- Understand Bengali and English.
- Follow the language requested by the user.
- Analyse uploaded images and audio when available.
- Never invent facts or personal information.
- Provide useful explanations and working code.
- Be professional and helpful.
"""

SYSTEM_INSTRUCTION = """
CORE RESPONSIBILITIES:

1. Give accurate and useful answers.
2. Understand Bengali and English.
3. Follow the user's requested language.
4. Answer directly inside the chat.
5. Never invent facts, sources or links.
6. Explain uncertainty honestly.
7. Help with programming, AI, business,
   graphic design, writing and education.
8. Provide complete code when requested.
9. Use available conversation history.
10. Avoid unnecessary repetition.
11. Explain technical instructions step by step.
12. Never claim actions you did not perform.
13. Analyse supplied media when supported.
14. Do not claim internet access unless available.

RESPONSE STYLE:
Professional, intelligent, clear and helpful.
Provide detailed answers when requested.
"""


def build_runtime_instruction(provider, model):
    return (
        FAHIM_AI_IDENTITY
        + SYSTEM_INSTRUCTION
        + f"""

CURRENT REQUEST RUNTIME:

Application: {APP_NAME}
Version: {APP_VERSION}
Creator: Fahim

ACTIVE PROVIDER:
{provider}

REQUESTED MODEL:
{model}

These values describe the provider selected
for this particular request.

Do not confuse configured providers with
the provider currently answering.
Never guess technical information.
"""
    )


# ==========================================================
# 3. STREAMLIT SECRETS
# ==========================================================

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_SECRET_KEY"]
except Exception as error:
    st.error("Required Streamlit Secrets are missing.")
    st.code(str(error))
    st.stop()

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", "")

PRIMARY_MODEL = st.secrets.get("PRIMARY_MODEL", "gemini-3.8-flash")

backup_config = st.secrets.get(
    "BACKUP_MODELS",
    ["gemini-3.7-flash", "gemini-3.6-flash"],
)

if isinstance(backup_config, str):
    BACKUP_MODELS = [
        item.strip()
        for item in backup_config.split(",")
        if item.strip()
    ]
else:
    BACKUP_MODELS = list(backup_config)

GROQ_MODEL = st.secrets.get(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)

OPENROUTER_MODEL = st.secrets.get(
    "OPENROUTER_MODEL",
    "openrouter/free",
)


# ==========================================================
# 4. API CLIENTS
# ==========================================================

@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)


@st.cache_resource(show_spinner=False)
def get_supabase_client(url, key):
    return create_client(url, key)


try:
    gemini_client = get_gemini_client(GEMINI_API_KEY)
    supabase = get_supabase_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as error:
    st.error("Connection initialization failed.")
    st.code(str(error))
    st.stop()


# ==========================================================
# 5. SESSION MANAGEMENT
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
# 6. SUPABASE PERMANENT CHAT HISTORY
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
            "content": content,
        }).execute()
        return True
    except Exception as error:
        st.error("Message could not be saved.")
        st.code(str(error))
        return False


def delete_chat_history():
    """Only called by the user's explicit Clear conversation button."""
    try:
        supabase.table("chat_history").delete().eq(
            "session_id", SESSION_ID
        ).execute()
        return True
    except Exception as error:
        st.error("Could not delete conversation.")
        st.code(str(error))
        return False


if not st.session_state.messages:
    try:
        st.session_state.messages = load_chat_history()
    except Exception as error:
        st.error("Could not restore chat history.")
        st.code(str(error))
        st.stop()


# ==========================================================
# 7. ERROR CLASSIFICATION
# ==========================================================

def is_quota_error(error):
    message = str(error).upper()
    return any(term in message for term in (
        "429",
        "RESOURCE_EXHAUSTED",
        "QUOTA_EXCEEDED",
        "RATE_LIMIT",
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
# 8. CONVERSATION HISTORY
# ==========================================================

def prepare_history(messages):
    recent = messages[-MAX_CONTEXT_MESSAGES:]

    while recent and recent[0].get("role") != "user":
        recent = recent[1:]

    contents = []

    for message in recent:
        role = "user" if message.get("role") == "user" else "model"
        content_text = message.get("content", "")

        if not isinstance(content_text, str):
            content_text = str(content_text)

        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=content_text)],
            )
        )

    return contents


def prepare_openai_history(contents, runtime_instruction):
    messages = [{
        "role": "system",
        "content": runtime_instruction,
    }]

    for item in contents:
        role = "user" if item.role == "user" else "assistant"

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
# 9. MULTIMODAL FILE PROCESSOR
# ==========================================================

def get_file_mime_type(uploaded_file):
    """Normalize browser-provided MIME types and infer from extension."""
    mime_type = (uploaded_file.type or "").lower().strip()

    if not mime_type or mime_type == "application/octet-stream":
        mime_type, _ = mimetypes.guess_type(uploaded_file.name)

    mime_type = (mime_type or "").lower().strip()
    return MIME_ALIASES.get(mime_type, mime_type)


def attach_media_to_history(contents, files):
    if not files:
        return contents

    if not contents:
        raise ValueError("No user message found for uploaded files.")

    file_payloads = []
    total_size = 0

    # Validate every file before constructing the Gemini request.
    for uploaded_file in files:
        data = uploaded_file.getvalue()
        mime_type = get_file_mime_type(uploaded_file)

        if not data:
            raise ValueError(f"The file is empty: {uploaded_file.name}")

        total_size += len(data)

        if mime_type not in ALLOWED_IMAGE_TYPES | ALLOWED_AUDIO_TYPES:
            raise ValueError(
                f"Unsupported file type: {uploaded_file.name} "
                f"({mime_type or 'unknown MIME type'})."
            )

        file_payloads.append((uploaded_file.name, data, mime_type))

    if total_size > MAX_UPLOAD_SIZE:
        raise ValueError(
            "Total upload size exceeds 30 MB. "
            "Please upload smaller files."
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
                f"Could not prepare {filename} for Gemini: {error}"
            ) from error

    last_message = contents[-1]

    if last_message.role != "user":
        raise ValueError("Attachments must be associated with a user message.")

    contents[-1] = types.Content(
        role="user",
        parts=list(last_message.parts or []) + media_parts,
    )

    return contents


# ==========================================================
# 10. PROVIDER CONFIGURATION
# ==========================================================

def get_providers():
    providers = [{
        "name": "Google Gemini",
        "type": "gemini",
        "model": PRIMARY_MODEL,
        "tier": "Primary",
    }]

    for model in BACKUP_MODELS:
        if model != PRIMARY_MODEL:
            providers.append({
                "name": "Google Gemini",
                "type": "gemini",
                "model": model,
                "tier": "Backup",
            })

    if GROQ_API_KEY:
        providers.append({
            "name": "Groq",
            "type": "openai",
            "model": GROQ_MODEL,
            "key": GROQ_API_KEY,
            "url": "https://api.groq.com/openai/v1",
            "tier": "Fallback",
        })

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
# 11. GEMINI STREAMING + ROBUST RESPONSE EXTRACTION
# ==========================================================

def extract_gemini_chunk_text(chunk):
    """
    Read text safely. Some SDK response chunks can have no text property,
    or .text can raise when the chunk contains no textual candidate part.
    """
    try:
        direct_text = chunk.text
        if direct_text:
            return direct_text
    except (AttributeError, ValueError, TypeError):
        pass
    except Exception:
        pass

    extracted = []

    try:
        candidates = chunk.candidates or []
    except Exception:
        candidates = []

    for candidate in candidates:
        try:
            candidate_content = candidate.content
            candidate_parts = candidate_content.parts or []
        except Exception:
            continue

        for part in candidate_parts:
            try:
                part_text = part.text
            except Exception:
                part_text = None

            if part_text:
                extracted.append(part_text)

    return "".join(extracted)


def gemini_chunk_diagnostics(chunk):
    details = []

    try:
        prompt_feedback = getattr(chunk, "prompt_feedback", None)
        if prompt_feedback:
            details.append(f"Prompt feedback: {prompt_feedback}")
    except Exception:
        pass

    try:
        for candidate in chunk.candidates or []:
            finish_reason = getattr(candidate, "finish_reason", None)
            if finish_reason:
                details.append(f"Finish reason: {finish_reason}")
    except Exception:
        pass

    return "\n".join(details)


def stream_gemini(provider, contents, placeholder, status):
    model = provider["model"]

    runtime_instruction = build_runtime_instruction(
        provider["name"],
        model,
    )

    config = types.GenerateContentConfig(
        system_instruction=runtime_instruction,
        temperature=0.7,
    )

    status.write(f"Sending request to Gemini model: {model}")

    stream = gemini_client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    )

    parts = []
    observed_model = None
    diagnostics = []
    started = time.monotonic()

    for chunk in stream:
        if time.monotonic() - started > REQUEST_TIMEOUT:
            raise TimeoutError("Gemini response timed out.")

        chunk_model = getattr(chunk, "model_version", None)
        if chunk_model:
            observed_model = chunk_model

        chunk_text = extract_gemini_chunk_text(chunk)

        if chunk_text:
            parts.append(chunk_text)
            placeholder.markdown("".join(parts) + " ▌")

        diagnostic = gemini_chunk_diagnostics(chunk)
        if diagnostic:
            diagnostics.append(diagnostic)

    answer = "".join(parts).strip()

    if not answer:
        diagnostic_text = "\n".join(diagnostics[-3:])
        raise RuntimeError(
            "Gemini completed the request but returned no readable text. "
            "The model may have returned a blocked, empty, or non-text response."
            + (f"\nGemini details:\n{diagnostic_text}" if diagnostic_text else "")
        )

    return answer, observed_model or model


# ==========================================================
# 12. GROQ / OPENROUTER TEXT STREAMING
# ==========================================================

def stream_openai_compatible(provider, contents, placeholder):
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

    messages = prepare_openai_history(contents, runtime_instruction)

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
            raise TimeoutError(f"{provider['name']} timed out.")

        chunk_model = getattr(chunk, "model", None)
        if chunk_model:
            observed_model = chunk_model

        if not chunk.choices:
            continue

        delta_content = chunk.choices[0].delta.content

        if isinstance(delta_content, str) and delta_content:
            parts.append(delta_content)
            placeholder.markdown("".join(parts) + " ▌")

        elif isinstance(delta_content, list):
            # Some compatible APIs return structured text content blocks.
            for block in delta_content:
                block_text = getattr(block, "text", None)
                if block_text:
                    parts.append(block_text)
                    placeholder.markdown("".join(parts) + " ▌")

    answer = "".join(parts).strip()

    if not answer:
        raise RuntimeError(
            f"{provider['name']} returned an empty response."
        )

    return answer, observed_model or model


# ==========================================================
# 13. HYBRID AI ROUTER
# ==========================================================

def generate_answer(contents, placeholder, status, has_media=False):
    providers = get_providers()

    if has_media:
        # Important: do not send media requests to text-only fallbacks.
        # Gemini receives the actual image/audio Part objects.
        providers = [
            provider for provider in providers
            if provider["type"] == "gemini"
        ]

    errors = []
    skip_remaining_gemini = False

    for provider in providers:
        name = provider["name"]
        model = provider["model"]
        provider_type = provider["type"]

        if provider_type == "gemini" and skip_remaining_gemini:
            continue

        status.update(
            label=f"Connecting to {name}...",
            state="running",
            expanded=True,
        )
        status.write(f"Requested model: {model}")

        if has_media:
            status.write("Preparing uploaded media for Gemini multimodal analysis.")

        status.write("Waiting for AI response...")
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
                label=f"Completed successfully: {name}",
                state="complete",
                expanded=False,
            )

            return answer, name, model, actual_model

        except Exception as error:
            error_text = str(error)

            errors.append(f"{name} ({model}): {error_text}")

            st.session_state.fallback_events.append({
                "from": name,
                "model": model,
                "error": error_text,
                "time": datetime.now().strftime("%H:%M:%S"),
            })

            placeholder.empty()

            if provider_type == "gemini" and is_quota_error(error):
                skip_remaining_gemini = True
                status.write(
                    "Gemini quota issue detected. "
                    "Skipping remaining Gemini models."
                )

            if is_auth_error(error):
                status.write("Authentication error detected.")

            status.write(
                f"{name} failed. Checking next compatible provider..."
            )

    status.update(
        label="All compatible AI providers failed.",
        state="error",
        expanded=True,
    )

    raise RuntimeError(
        "No compatible AI provider could generate a response:\n\n"
        + "\n\n".join(errors)
    )


# ==========================================================
# 14. INTERFACE DESIGN
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
# 15. SIDEBAR
# ==========================================================

with st.sidebar:
    st.title("⚙️ Settings")

    st.success("Gemini connection configured")
    st.success("Supabase configured")

    if GROQ_API_KEY:
        st.success("Groq configured")
    else:
        st.warning("Groq API key missing")

    if OPENROUTER_API_KEY:
        st.success("OpenRouter configured")
    else:
        st.warning("OpenRouter API key missing")

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

    st.metric("Total messages", len(st.session_state.messages))
    st.metric("Total requests", st.session_state.request_count)
    st.metric("Fallback events", len(st.session_state.fallback_events))

    with st.expander("Provider fallback history"):
        if st.session_state.fallback_events:
            for event in reversed(st.session_state.fallback_events[-10:]):
                st.write(f"**{event['from']}** — {event['model']}")
                st.caption(event["time"])
                st.caption(event["error"][:500])
        else:
            st.caption("No provider failures recorded.")

    st.divider()

    if st.button("🗑️ Clear conversation", use_container_width=True):
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
    - Groq fallback for text
    - OpenRouter fallback for text
    - Runtime provider detection
    - Runtime model identification
    - Live text streaming
    - Automatic provider switching
    - Permanent text chat history
    - Multiple image uploads
    - Multiple audio uploads
    - Image understanding
    - Audio understanding
    - Bengali and English
    - Programming assistance
    - Business assistance
    - Creative design assistance
    """)

    st.divider()
    st.caption("FAHIM GRAPHIC DESIGN")
    st.caption("Creative Design. Professional Results.")


# ==========================================================
# 16. MAIN HEADER
# ==========================================================

st.title("🤖 FAHIM AI")

st.caption(
    "Hybrid Multimodal AI Assistant | "
    "Gemini + Groq + OpenRouter | "
    "Permanent Chat History"
)

st.divider()


# ==========================================================
# 17. DISPLAY CHAT HISTORY
# ==========================================================

for message in st.session_state.messages:
    role = message.get("role")

    if role not in ("user", "assistant"):
        continue

    with st.chat_message(role):
        st.markdown(message.get("content", ""))


# ==========================================================
# 18. MULTIPLE FILE UPLOAD
# ==========================================================

st.subheader("📎 Upload Images & Audio")

upload_key = (
    f"fahim_uploads_"
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
    st.success(f"{len(uploaded_files)} file(s) selected.")

    for uploaded_file in uploaded_files:
        mime_type = get_file_mime_type(uploaded_file)

        st.caption(
            f"📄 {uploaded_file.name} | "
            f"{mime_type or 'Unknown type'} | "
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
# 19. CHAT INPUT
# ==========================================================

user_prompt = st.chat_input("Ask FAHIM AI anything...")


# ==========================================================
# 20. PROCESS USER REQUEST
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
            st.caption("📎 " + ", ".join(file.name for file in files))

    user_saved = save_message("user", user_prompt)

    if not user_saved:
        st.warning(
            "Message is visible in this session, "
            "but permanent saving failed."
        )

    # Build the request without changing or deleting stored history.
    try:
        api_history = prepare_history(st.session_state.messages)
        api_history = attach_media_to_history(api_history, files)

    except Exception as error:
        st.error(f"Attachment processing error: {error}")
        st.warning(
            "Your existing chat history has NOT been deleted. "
            "The text of this request remains in the conversation."
        )

        # Do not call delete_chat_history() here.
        st.session_state.upload_widget_version += 1
        st.stop()

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
                    api_history,
                    placeholder,
                    status,
                    has_media=bool(files),
                )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
            })

            assistant_saved = save_message("assistant", answer)

            st.caption(f"⚡ Active provider: {provider}")
            st.caption(f"🧠 Requested model: {requested_model}")
            st.caption(f"🔍 Reported response model: {actual_model}")

            if assistant_saved:
                st.caption("☁️ Permanently saved to Supabase")
            else:
                st.warning(
                    "Answer generated, but permanent saving failed."
                )

        except Exception as error:
            st.session_state.last_error = str(error)
            placeholder.empty()

            st.error("FAHIM AI could not complete the response.")

            with st.expander("Technical error details", expanded=True):
                st.code(str(error))

            st.info(
                "Your existing chat history has NOT been deleted. "
                "Check the Gemini model name, API key, quota and media support."
            )

    # Uploaded media is not persisted to Supabase. The user can upload it
    # again if needed; the text conversation remains permanently stored.
    st.session_state.upload_widget_version += 1
    st.rerun()


# ==========================================================
# 21. FOOTER
# ==========================================================

st.divider()

st.caption(
    "© 2026 FAHIM AI | "
    "Gemini + Groq + OpenRouter + Supabase | "
    "Version 4.1"
)
