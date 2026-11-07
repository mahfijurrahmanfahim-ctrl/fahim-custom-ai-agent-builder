
# ============================================================
# FAHIM AI v5.1
# HYBRID MULTI-PROVIDER MULTIMODAL AI ASSISTANT
#
# NaraRouter + Gemini + Groq + OpenRouter
# Supabase Permanent Chat History
# Multiple Images / Audio / Documents
# Image Search
# Automatic Provider Fallback
# Streaming Responses
# Bengali + English
# ============================================================

import os
import io
import json
import time
import uuid
import mimetypes
import traceback

from datetime import datetime, timezone

import streamlit as st

from openai import OpenAI
from google import genai
from google.genai import types
from supabase import create_client


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="FAHIM AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 2. APP CONFIGURATION
# ============================================================

APP_NAME = "FAHIM AI"
APP_VERSION = "5.1"

NARA_BASE_URL = "https://router.bynara.id/v1"

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

NARA_DEFAULT_MODEL = "auto/bynara"

GEMINI_DEFAULT_MODEL = "gemini-3.8-flash"

GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"

OPENROUTER_DEFAULT_MODEL = "openai/gpt-4o-mini"

MAX_HISTORY_MESSAGES = 30


# ============================================================
# 3. SECRET MANAGEMENT
# ============================================================

def get_secret(name, default=None):

    try:
        value = st.secrets.get(name, default)

        if value is not None:
            return value

    except Exception:
        pass

    return os.getenv(name, default)


def get_string_secret(name, default=""):

    value = get_secret(name, default)

    if value is None:
        return default

    return str(value).strip()


NARA_API_KEY = get_string_secret("NARA_API_KEY")

NARA_MODEL = get_string_secret(
    "NARA_MODEL",
    NARA_DEFAULT_MODEL
)

GEMINI_API_KEY = get_string_secret("GEMINI_API_KEY")

GROQ_API_KEY = get_string_secret("GROQ_API_KEY")

OPENROUTER_API_KEY = get_string_secret("OPENROUTER_API_KEY")

SUPABASE_URL = get_string_secret("SUPABASE_URL")

SUPABASE_KEY = (
    get_string_secret("SUPABASE_SECRET_KEY")
    or get_string_secret("SUPABASE_KEY")
)

PRIMARY_MODEL = get_string_secret(
    "PRIMARY_MODEL",
    GEMINI_DEFAULT_MODEL
)

GROQ_MODEL = get_string_secret(
    "GROQ_MODEL",
    GROQ_DEFAULT_MODEL
)

OPENROUTER_MODEL = get_string_secret(
    "OPENROUTER_MODEL",
    OPENROUTER_DEFAULT_MODEL
)


def get_backup_models():

    models = get_secret(
        "BACKUP_MODELS",
        ["gemini-3.7-flash", "gemini-3.6-flash"]
    )

    if isinstance(models, str):

        try:
            models = json.loads(models)
        except Exception:
            models = [
                x.strip()
                for x in models.split(",")
                if x.strip()
            ]

    if not isinstance(models, list):
        return []

    return [str(x).strip() for x in models if str(x).strip()]


BACKUP_MODELS = get_backup_models()


# ============================================================
# 4. SESSION STATE
# ============================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "history_loaded" not in st.session_state:
    st.session_state.history_loaded = False

if "active_provider" not in st.session_state:
    st.session_state.active_provider = "Not connected"

if "active_model" not in st.session_state:
    st.session_state.active_model = "None"

if "fallback_count" not in st.session_state:
    st.session_state.fallback_count = 0

if "request_count" not in st.session_state:
    st.session_state.request_count = 0

if "last_error" not in st.session_state:
    st.session_state.last_error = None

if "nara_models" not in st.session_state:
    st.session_state.nara_models = []

if "nara_discovery_error" not in st.session_state:
    st.session_state.nara_discovery_error = None

if "selected_nara_model" not in st.session_state:
    st.session_state.selected_nara_model = NARA_MODEL


# ============================================================
# 5. SYSTEM INSTRUCTIONS
# ============================================================

SYSTEM_PROMPT = """
You are FAHIM AI, an advanced hybrid multimodal AI assistant.

Your creator is Fahim.

You support:
- English
- Bengali
- Text conversations
- Image understanding
- Audio understanding
- Document understanding
- Web and image search when tools are available
- Coding and technical assistance

IMPORTANT RULES:

1. Never invent technical information.
2. Never pretend a provider is active without evidence.
3. Distinguish configured providers from the provider
   actually handling the current request.
4. Do not claim to have searched the internet unless
   a search tool actually returned results.
5. Do not invent image search results.
6. Preserve conversation context.
7. Give complete code when requested.
8. Answer in the user's language.
9. Be concise when the user asks simple questions.

The application provides runtime provider information.
Use it rather than guessing.
"""


# ============================================================
# 6. SUPABASE CONNECTION
# ============================================================

@st.cache_resource(show_spinner=False)
def get_supabase():

    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        return create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )

    except Exception as e:
        st.session_state.last_error = str(e)
        return None


supabase = get_supabase()


# ============================================================
# 7. PERMANENT CHAT HISTORY
# ============================================================

def load_chat_history():

    if st.session_state.history_loaded:
        return

    if supabase is None:
        st.session_state.history_loaded = True
        return

    try:

        response = (
            supabase
            .table("chat_history")
            .select("role, content")
            .eq(
                "session_id",
                st.session_state.session_id
            )
            .order("created_at", desc=False)
            .execute()
        )

        rows = response.data or []

        st.session_state.messages = [
            {
                "role": row["role"],
                "content": row["content"]
            }
            for row in rows
            if row.get("role") in ["user", "assistant"]
        ]

    except Exception as e:

        st.session_state.last_error = (
            "Supabase history loading error: " + str(e)
        )

    st.session_state.history_loaded = True


def save_message(role, content):

    if supabase is None:
        return False

    try:

        supabase.table("chat_history").insert({

            "session_id": st.session_state.session_id,

            "role": role,

            "content": str(content),

        }).execute()

        return True

    except Exception as e:

        st.session_state.last_error = (
            "Supabase save error: " + str(e)
        )

        return False


def clear_chat_history():

    if supabase is not None:

        try:

            supabase.table("chat_history").delete().eq(
                "session_id",
                st.session_state.session_id
            ).execute()

        except Exception as e:

            st.error(f"History deletion failed: {e}")
            return

    st.session_state.messages = []

    st.session_state.history_loaded = True

    st.rerun()


load_chat_history()


# ============================================================
# 8. PROVIDER CLIENTS
# ============================================================

def get_nara_client():

    if not NARA_API_KEY:
        raise RuntimeError("NARA_API_KEY is missing.")

    return OpenAI(
        api_key=NARA_API_KEY,
        base_url=NARA_BASE_URL,
        timeout=90,
        max_retries=1
    )


def get_groq_client():

    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing.")

    return OpenAI(
        api_key=GROQ_API_KEY,
        base_url=GROQ_BASE_URL,
        timeout=90
    )


def get_openrouter_client():

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

    return OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        timeout=90
    )


def get_gemini_client():

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    return genai.Client(
        api_key=GEMINI_API_KEY
    )


# ============================================================
# 9. NARAROUTER MODEL DISCOVERY
# ============================================================

def discover_nara_models():

    if not NARA_API_KEY:

        st.session_state.nara_discovery_error = (
            "NARA_API_KEY is missing."
        )

        return []

    try:

        client = get_nara_client()

        response = client.models.list()

        models = []

        for model in response.data:

            model_id = getattr(model, "id", None)

            if model_id:
                models.append(model_id)

        st.session_state.nara_models = models

        st.session_state.nara_discovery_error = None

        return models

    except Exception as e:

        st.session_state.nara_discovery_error = str(e)

        # IMPORTANT:
        # Model discovery failure does not disable
        # the configured NaraRouter model.

        st.session_state.nara_models = []

        return []


# ============================================================
# 10. CONVERSATION HISTORY FORMATTING
# ============================================================

def get_conversation():

    messages = []

    recent = st.session_state.messages[-MAX_HISTORY_MESSAGES:]

    for item in recent:

        role = item.get("role")

        content = item.get("content", "")

        if role in ["user", "assistant"]:

            messages.append({
                "role": role,
                "content": content
            })

    return messages


def build_openai_messages(user_text):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(get_conversation())

    messages.append({
        "role": "user",
        "content": user_text
    })

    return messages


def build_gemini_contents(user_text, attachments=None):

    contents = []

    for item in get_conversation():

        contents.append({
            "role": (
                "model"
                if item["role"] == "assistant"
                else "user"
            ),
            "parts": [
                {
                    "text": item["content"]
                }
            ]
        })

    parts = [
        types.Part.from_text(
            text=SYSTEM_PROMPT
        )
    ]

    parts.append(
        types.Part.from_text(
            text=user_text
        )
    )

    if attachments:

        for uploaded_file in attachments:

            file_bytes = uploaded_file.getvalue()

            mime_type = (
                uploaded_file.type
                or mimetypes.guess_type(
                    uploaded_file.name
                )[0]
                or "application/octet-stream"
            )

            parts.append(
                types.Part.from_bytes(
                    data=file_bytes,
                    mime_type=mime_type
                )
            )

    contents.append({
        "role": "user",
        "parts": parts
    })

    return contents


# ============================================================
# 11. GEMINI GENERATION
# ============================================================

def generate_gemini(user_text, attachments=None):

    client = get_gemini_client()

    models = []

    if PRIMARY_MODEL:
        models.append(PRIMARY_MODEL)

    for model in BACKUP_MODELS:

        if model not in models:
            models.append(model)

    last_error = None

    for model in models:

        try:

            contents = build_gemini_contents(
                user_text,
                attachments
            )

            config = types.GenerateContentConfig(
                temperature=0.7
            )

            response_stream = (
                client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=config
                )
            )

            result = ""

            for chunk in response_stream:

                if chunk.text:

                    result += chunk.text

                    yield {
                        "type": "token",
                        "text": chunk.text,
                        "provider": "Gemini",
                        "model": model
                    }

            if not result:
                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            yield {
                "type": "done",
                "provider": "Gemini",
                "model": model
            }

            return

        except Exception as e:

            last_error = e

            error_text = str(e).lower()

            # Skip remaining Gemini models on quota errors.

            if (
                "quota" in error_text
                or "resource_exhausted" in error_text
                or "429" in error_text
            ):
                break

            if (
                "invalid api key" in error_text
                or "unauthorized" in error_text
                or "403" in error_text
            ):
                break

    raise RuntimeError(
        f"All Gemini models failed: {last_error}"
    )


# ============================================================
# 12. OPENAI-COMPATIBLE STREAMING
# ============================================================

def generate_openai_stream(
    provider,
    client,
    model,
    messages
):

    stream = client.chat.completions.create(

        model=model,

        messages=messages,

        temperature=0.7,

        stream=True,

    )

    result = ""

    actual_model = model

    for chunk in stream:

        if getattr(chunk, "model", None):
            actual_model = chunk.model

        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        content = getattr(delta, "content", None)

        if isinstance(content, str) and content:

            result += content

            yield {
                "type": "token",
                "text": content,
                "provider": provider,
                "model": actual_model
            }

    if not result:

        raise RuntimeError(
            f"{provider} returned an empty response."
        )

    yield {
        "type": "done",
        "provider": provider,
        "model": actual_model
    }


# ============================================================
# 13. PROVIDER FALLBACK ENGINE
# ============================================================

def generate_response(user_text, attachments=None):

    st.session_state.request_count += 1

    errors = []

    has_media = bool(attachments)

    # Media requests must go to Gemini because
    # the other configured providers are text-only here.

    if has_media:

        try:

            yield from generate_gemini(
                user_text,
                attachments
            )

            return

        except Exception as e:

            raise RuntimeError(
                "Multimodal Gemini processing failed: "
                + str(e)
            )

    messages = build_openai_messages(user_text)

    # --------------------------------------------------------
    # PROVIDER 1: NARAROUTER
    # --------------------------------------------------------

    if NARA_API_KEY:

        try:

            client = get_nara_client()

            model = (
                st.session_state.selected_nara_model
                or NARA_MODEL
                or NARA_DEFAULT_MODEL
            )

            yield from generate_openai_stream(
                "NaraRouter",
                client,
                model,
                messages
            )

            return

        except Exception as e:

            errors.append(
                "NaraRouter: " + str(e)
            )

            st.session_state.fallback_count += 1

    # --------------------------------------------------------
    # PROVIDER 2: GEMINI
    # --------------------------------------------------------

    if GEMINI_API_KEY:

        try:

            yield from generate_gemini(user_text)

            return

        except Exception as e:

            errors.append(
                "Gemini: " + str(e)
            )

            st.session_state.fallback_count += 1

    # --------------------------------------------------------
    # PROVIDER 3: GROQ
    # --------------------------------------------------------

    if GROQ_API_KEY:

        try:

            client = get_groq_client()

            yield from generate_openai_stream(
                "Groq",
                client,
                GROQ_MODEL,
                messages
            )

            return

        except Exception as e:

            errors.append(
                "Groq: " + str(e)
            )

            st.session_state.fallback_count += 1

    # --------------------------------------------------------
    # PROVIDER 4: OPENROUTER
    # --------------------------------------------------------

    if OPENROUTER_API_KEY:

        try:

            client = get_openrouter_client()

            yield from generate_openai_stream(
                "OpenRouter",
                client,
                OPENROUTER_MODEL,
                messages
            )

            return

        except Exception as e:

            errors.append(
                "OpenRouter: " + str(e)
            )

            st.session_state.fallback_count += 1

    # --------------------------------------------------------
    # ALL PROVIDERS FAILED
    # --------------------------------------------------------

    raise RuntimeError(
        "All available AI providers failed.\n\n"
        + "\n".join(errors)
    )


# ============================================================
# 14. IMAGE SEARCH
# ============================================================

def image_search(query, limit=8):

    try:

        from ddgs import DDGS

        results = DDGS().images(
            query,
            max_results=limit
        )

        return list(results)

    except ImportError:

        st.error(
            "Image search package missing. "
            "Add ddgs to requirements.txt."
        )

        return []

    except Exception as e:

        st.error(
            f"Image search failed: {e}"
        )

        return []


# ============================================================
# 15. SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🤖 FAHIM AI")

    st.caption(
        f"Hybrid Multimodal Assistant v{APP_VERSION}"
    )

    st.divider()

    st.subheader("⚙️ Provider Settings")

    st.write("**Primary:** NaraRouter")

    st.write(
        f"**Nara model:** {st.session_state.selected_nara_model}"
    )

    if NARA_API_KEY:

        st.success("NaraRouter API key configured")

    else:

        st.warning("NaraRouter API key missing")

    if st.button(
        "🔄 Discover NaraRouter Models",
        use_container_width=True
    ):

        with st.spinner("Discovering models..."):
            discover_nara_models()

        st.rerun()

    if st.session_state.nara_models:

        options = list(
            dict.fromkeys(
                [NARA_MODEL] + st.session_state.nara_models
            )
        )

        current = st.session_state.selected_nara_model

        if current not in options:
            options.insert(0, current)

        selected = st.selectbox(
            "NaraRouter Model",
            options=options,
            index=options.index(current)
        )

        st.session_state.selected_nara_model = selected

    else:

        # Keep the configured model available even
        # when /models discovery fails.

        st.selectbox(
            "NaraRouter Model",
            options=[NARA_MODEL],
            index=0,
            disabled=True
        )

        if st.session_state.nara_discovery_error:

            with st.expander("Model discovery details"):

                st.code(
                    st.session_state.nara_discovery_error
                )

            st.caption(
                "Configured model remains available. "
                "Model discovery is optional."
            )

    st.divider()

    st.subheader("🔌 Available Providers")

    providers = [
        ("NaraRouter", NARA_API_KEY),
        ("Gemini", GEMINI_API_KEY),
        ("Groq", GROQ_API_KEY),
        ("OpenRouter", OPENROUTER_API_KEY),
    ]

    for name, key in providers:

        if key:
            st.write(f"🟢 {name}")
        else:
            st.write(f"⚪ {name}")

    st.divider()

    st.subheader("📊 Statistics")

    st.metric(
        "Total Messages",
        len(st.session_state.messages)
    )

    st.metric(
        "Requests",
        st.session_state.request_count
    )

    st.metric(
        "Fallback Events",
        st.session_state.fallback_count
    )

    st.metric(
        "Current Provider",
        st.session_state.active_provider
    )

    st.metric(
        "Current Model",
        st.session_state.active_model
    )

    st.divider()

    if supabase:

        st.success("Supabase connected")

    else:

        st.warning("Supabase not connected")

    st.divider()

    st.subheader("💬 Chat Management")

    if st.button(
        "📥 Export Chat",
        use_container_width=True
    ):

        chat_json = json.dumps(
            st.session_state.messages,
            ensure_ascii=False,
            indent=2
        )

        st.download_button(
            "Download JSON",
            data=chat_json,
            file_name="fahim_ai_chat.json",
            mime="application/json",
            use_container_width=True
        )

    if st.button(
        "🗑️ Clear Current Chat",
        use_container_width=True
    ):

        st.session_state.confirm_clear = True

    if st.session_state.get("confirm_clear", False):

        st.warning(
            "Only this session's saved messages will be deleted."
        )

        if st.button("Confirm Delete", type="primary"):

            st.session_state.confirm_clear = False

            clear_chat_history()

        if st.button("Cancel"):

            st.session_state.confirm_clear = False

            st.rerun()


# ============================================================
# 16. MAIN INTERFACE
# ============================================================

st.title("🤖 FAHIM AI")

st.caption(
    "Your Hybrid AI Assistant | "
    "NaraRouter + Gemini + Groq + OpenRouter"
)

st.divider()


# ============================================================
# 17. IMAGE SEARCH INTERFACE
# ============================================================

with st.expander("🔎 Search Images"):

    search_query = st.text_input(
        "What image do you want to find?",
        key="image_search_query"
    )

    if st.button("Search Images"):

        if search_query.strip():

            with st.spinner("Searching images..."):

                results = image_search(
                    search_query.strip()
                )

            if results:

                st.success(
                    f"Found {len(results)} image results."
                )

                columns = st.columns(2)

                for index, result in enumerate(results):

                    image_url = result.get("image")

                    title = result.get(
                        "title",
                        "Image result"
                    )

                    source = result.get("source", "")

                    with columns[index % 2]:

                        if image_url:

                            try:

                                st.image(
                                    image_url,
                                    caption=title,
                                    use_container_width=True
                                )

                            except Exception:
                                st.write(title)

                        if source:
                            st.caption(source)

                        if image_url:
                            st.markdown(
                                f"[Open image]({image_url})"
                            )

            else:

                st.info("No image results found.")


# ============================================================
# 18. DISPLAY CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ============================================================
# 19. MULTIMODAL UPLOAD
# ============================================================

st.subheader("📎 Attach Files")

uploaded_files = st.file_uploader(

    "Upload multiple images, audio files or documents",

    type=[
        "jpg",
        "jpeg",
        "png",
        "webp",
        "mp3",
        "wav",
        "m4a",
        "ogg",
        "flac",
        "pdf",
        "txt",
        "md"
    ],

    accept_multiple_files=True,

    key="fahim_uploads"

)

if uploaded_files:

    st.write(
        f"Attached files: {len(uploaded_files)}"
    )

    for uploaded in uploaded_files:

        st.caption(
            f"📄 {uploaded.name} "
            f"({uploaded.size / 1024:.1f} KB)"
        )


# ============================================================
# 20. CHAT INPUT
# ============================================================

user_input = st.chat_input(
    "Message FAHIM AI..."
)


# ============================================================
# 21. PROCESS USER MESSAGE
# ============================================================

if user_input:

    user_input = user_input.strip()

    if not user_input and not uploaded_files:
        st.stop()

    attachment_info = ""

    if uploaded_files:

        attachment_info = "\n\nAttached files:\n" + "\n".join(
            f"- {file.name}"
            for file in uploaded_files
        )

    display_message = user_input or "Please analyze my attached files."

    if attachment_info:
        display_message += attachment_info

    # Save user message before generation.

    st.session_state.messages.append({

        "role": "user",

        "content": display_message

    })

    save_message(
        "user",
        display_message
    )

    with st.chat_message("user"):

        st.markdown(display_message)

    # --------------------------------------------------------
    # ASSISTANT RESPONSE
    # --------------------------------------------------------

    with st.chat_message("assistant"):

        response_placeholder = st.empty()

        provider_placeholder = st.empty()

        full_response = ""

        selected_provider = "Unknown"

        selected_model = "Unknown"

        try:

            with st.spinner("FAHIM AI is thinking..."):

                for event in generate_response(
                    user_input or "Analyze the attached files.",
                    uploaded_files
                ):

                    if event["type"] == "token":

                        full_response += event["text"]

                        selected_provider = event["provider"]

                        selected_model = event["model"]

                        response_placeholder.markdown(
                            full_response + "▌"
                        )

                    elif event["type"] == "done":

                        selected_provider = event["provider"]

                        selected_model = event["model"]

            response_placeholder.markdown(
                full_response
            )

            st.session_state.active_provider = selected_provider

            st.session_state.active_model = selected_model

            provider_placeholder.caption(
                f"⚡ Provider: {selected_provider} | "
                f"Model: {selected_model}"
            )

            # Save assistant response permanently.

            st.session_state.messages.append({

                "role": "assistant",

                "content": full_response

            })

            save_message(
                "assistant",
                full_response
            )

        except Exception as e:

            error_message = str(e)

            st.session_state.last_error = error_message

            st.error(
                "AI request failed."
            )

            with st.expander("Technical error details"):

                st.code(error_message)

            # Do not save an error as an assistant answer.

            st.session_state.active_provider = "Failed"

            st.session_state.active_model = "None"


# ============================================================
# 22. FOOTER
# ============================================================

st.divider()

st.caption(
    f"FAHIM AI v{APP_VERSION} | "
    "Hybrid Multimodal AI Assistant | "
    "Powered by Fahim"
)
