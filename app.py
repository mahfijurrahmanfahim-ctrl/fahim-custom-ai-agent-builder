
# ============================================================
# FAHIM AI v5.2
# HYBRID MULTI-PROVIDER MULTIMODAL AI ASSISTANT
#
# NaraRouter + Gemini + Groq + OpenRouter
# Supabase Permanent Chat History
# Multiple Images / Audio / Documents
# Image Search
# Automatic Provider Fallback
# Safe Response Handling
# Bengali + English
# ============================================================

import os
import json
import mimetypes
import uuid

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
APP_VERSION = "5.2"

NARA_BASE_URL = "https://router.bynara.id/v1"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

NARA_DEFAULT_MODEL = "auto/bynara"
GEMINI_DEFAULT_MODEL = "gemini-3.8-flash"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"
OPENROUTER_DEFAULT_MODEL = "openai/gpt-4o-mini"

# Request timeouts in seconds
NARA_TIMEOUT = 12
GROQ_TIMEOUT = 15
OPENROUTER_TIMEOUT = 15
GEMINI_TIMEOUT_MS = 15000

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
                item.strip()
                for item in models.split(",")
                if item.strip()
            ]

    if not isinstance(models, list):
        return []

    return [
        str(item).strip()
        for item in models
        if str(item).strip()
    ]


BACKUP_MODELS = get_backup_models()


# ============================================================
# 4. SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "session_id": str(uuid.uuid4()),
    "messages": [],
    "history_loaded": False,
    "active_provider": "Not connected",
    "active_model": "None",
    "fallback_count": 0,
    "request_count": 0,
    "last_error": None,
    "nara_models": [],
    "nara_discovery_error": None,
    "selected_nara_model": NARA_MODEL,
    "confirm_clear": False
}

for key, value in DEFAULT_STATE.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# 5. SYSTEM PROMPT
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
- Coding and technical assistance
- Web and image search when tools are available

IMPORTANT RULES:

1. Never invent technical information.
2. Never pretend a provider is active without evidence.
3. Distinguish configured providers from the provider
   actually handling the current request.
4. Never claim an internet search happened unless
   a search tool actually returned results.
5. Never invent image search results.
6. Preserve conversation context.
7. Give complete code when requested.
8. Answer in the user's language.
9. Be concise when the user asks simple questions.
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

    except Exception:
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

    except Exception as error:

        st.session_state.last_error = (
            "History loading error: " + str(error)
        )

    st.session_state.history_loaded = True


def save_message(role, content):

    if supabase is None:
        return False

    try:

        supabase.table("chat_history").insert({
            "session_id": st.session_state.session_id,
            "role": role,
            "content": str(content)
        }).execute()

        return True

    except Exception as error:

        st.session_state.last_error = (
            "Supabase save error: " + str(error)
        )

        return False


def clear_chat_history():

    if supabase is not None:

        try:

            supabase.table("chat_history").delete().eq(
                "session_id",
                st.session_state.session_id
            ).execute()

        except Exception as error:

            st.error(f"History deletion failed: {error}")
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
        timeout=NARA_TIMEOUT,
        max_retries=0
    )


def get_groq_client():

    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing.")

    return OpenAI(
        api_key=GROQ_API_KEY,
        base_url=GROQ_BASE_URL,
        timeout=GROQ_TIMEOUT,
        max_retries=0
    )


def get_openrouter_client():

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

    return OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        timeout=OPENROUTER_TIMEOUT,
        max_retries=0
    )


def get_gemini_client():

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    return genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(
            timeout=GEMINI_TIMEOUT_MS
        )
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

    except Exception as error:

        st.session_state.nara_models = []

        st.session_state.nara_discovery_error = str(error)

        return []


# ============================================================
# 10. CONVERSATION HISTORY
# ============================================================

def get_previous_conversation():

    # The latest user message has already been saved
    # before generation. Exclude it here to prevent
    # sending the same question twice.

    previous = st.session_state.messages[:-1]

    recent = previous[-MAX_HISTORY_MESSAGES:]

    result = []

    for item in recent:

        role = item.get("role")
        content = item.get("content", "")

        if role in ["user", "assistant"] and content:

            result.append({
                "role": role,
                "content": content
            })

    return result


def build_openai_messages(user_text):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(get_previous_conversation())

    messages.append({
        "role": "user",
        "content": user_text
    })

    return messages


def build_gemini_contents(user_text, attachments=None):

    contents = []

    for item in get_previous_conversation():

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
        ),
        types.Part.from_text(
            text=user_text
        )
    ]

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

def generate_gemini_text(user_text, attachments=None):

    client = get_gemini_client()

    models = []

    if PRIMARY_MODEL:
        models.append(PRIMARY_MODEL)

    for model in BACKUP_MODELS:

        if model not in models:
            models.append(model)

    if not models:
        raise RuntimeError("No Gemini model configured.")

    errors = []

    contents = build_gemini_contents(
        user_text,
        attachments
    )

    config = types.GenerateContentConfig(
        temperature=0.7
    )

    for model in models:

        try:

            response_stream = (
                client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=config
                )
            )

            # Buffer the complete answer before displaying it.
            # This prevents a failed provider's partial output
            # from being mixed with a fallback answer.

            result = ""

            for chunk in response_stream:

                if chunk.text:
                    result += chunk.text

            if not result.strip():

                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            return result, model

        except Exception as error:

            errors.append(
                f"{model}: {str(error)}"
            )

            error_text = str(error).lower()

            if (
                "quota" in error_text
                or "resource_exhausted" in error_text
                or "429" in error_text
                or "invalid api key" in error_text
                or "unauthorized" in error_text
                or "403" in error_text
            ):
                break

    raise RuntimeError(
        "Gemini failed: " + " | ".join(errors)
    )


# ============================================================
# 12. OPENAI-COMPATIBLE GENERATION
# ============================================================

def generate_openai_text(
    provider,
    client,
    model,
    messages
):

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        stream=False
    )

    if not response.choices:

        raise RuntimeError(
            f"{provider} returned no choices."
        )

    content = response.choices[0].message.content

    if not isinstance(content, str) or not content.strip():

        raise RuntimeError(
            f"{provider} returned an empty response."
        )

    actual_model = getattr(
        response,
        "model",
        None
    ) or model

    return content, actual_model


# ============================================================
# 13. PROVIDER FALLBACK ENGINE
# ============================================================

def generate_response(user_text, attachments=None):

    st.session_state.request_count += 1

    errors = []

    has_media = bool(attachments)

    # --------------------------------------------------------
    # MULTIMODAL REQUESTS
    # --------------------------------------------------------

    if has_media:

        if not GEMINI_API_KEY:

            raise RuntimeError(
                "Attachments require Gemini, but GEMINI_API_KEY "
                "is not configured."
            )

        try:

            result, model = generate_gemini_text(
                user_text,
                attachments
            )

            yield {
                "type": "token",
                "text": result,
                "provider": "Gemini",
                "model": model
            }

            yield {
                "type": "done",
                "provider": "Gemini",
                "model": model
            }

            return

        except Exception as error:

            raise RuntimeError(
                "Multimodal Gemini processing failed: "
                + str(error)
            )

    # --------------------------------------------------------
    # TEXT REQUESTS
    # --------------------------------------------------------

    messages = build_openai_messages(user_text)

    providers = []

    if NARA_API_KEY:

        providers.append((
            "NaraRouter",
            get_nara_client,
            (
                st.session_state.selected_nara_model
                or NARA_MODEL
                or NARA_DEFAULT_MODEL
            )
        ))

    if GEMINI_API_KEY:

        providers.append((
            "Gemini",
            None,
            PRIMARY_MODEL
        ))

    if GROQ_API_KEY:

        providers.append((
            "Groq",
            get_groq_client,
            GROQ_MODEL
        ))

    if OPENROUTER_API_KEY:

        providers.append((
            "OpenRouter",
            get_openrouter_client,
            OPENROUTER_MODEL
        ))

    if not providers:

        raise RuntimeError(
            "No AI provider is configured. "
            "Please add at least one API key."
        )

    # --------------------------------------------------------
    # TRY EACH PROVIDER
    # --------------------------------------------------------

    for provider, client_factory, model in providers:

        try:

            if provider == "Gemini":

                result, actual_model = generate_gemini_text(
                    user_text
                )

            else:

                client = client_factory()

                result, actual_model = generate_openai_text(
                    provider,
                    client,
                    model,
                    messages
                )

            # Only display after a provider has succeeded.
            yield {
                "type": "token",
                "text": result,
                "provider": provider,
                "model": actual_model
            }

            yield {
                "type": "done",
                "provider": provider,
                "model": actual_model
            }

            return

        except Exception as error:

            errors.append(
                f"{provider}: {str(error)}"
            )

            st.session_state.fallback_count += 1

            continue

    raise RuntimeError(
        "All configured AI providers failed.\n\n"
        + "\n\n".join(errors)
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

    except Exception as error:

        st.error(
            f"Image search failed: {error}"
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
        f"**Nara model:** "
        f"{st.session_state.selected_nara_model}"
    )

    if NARA_API_KEY:
        st.success("NaraRouter API key configured")
    else:
        st.warning("NaraRouter API key missing")

    if st.button(
        "🔄 Discover NaraRouter Models",
        width="stretch"
    ):

        with st.spinner("Discovering NaraRouter models..."):
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
                "Model discovery is optional. "
                "The configured model can still be tested."
            )

    st.divider()

    st.subheader("🔌 Available Providers")

    providers = [
        ("NaraRouter", NARA_API_KEY),
        ("Gemini", GEMINI_API_KEY),
        ("Groq", GROQ_API_KEY),
        ("OpenRouter", OPENROUTER_API_KEY)
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

    if st.session_state.last_error:

        with st.expander("Last application error"):

            st.code(
                st.session_state.last_error
            )

    st.divider()

    st.subheader("💬 Chat Management")

    if st.button(
        "📥 Export Chat",
        width="stretch"
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
            width="stretch"
        )

    if st.button(
        "🗑️ Clear Current Chat",
        width="stretch"
    ):

        st.session_state.confirm_clear = True

    if st.session_state.confirm_clear:

        st.warning(
            "Only this session's saved messages will be deleted."
        )

        if st.button(
            "Confirm Delete",
            type="primary"
        ):

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
                                    width="stretch"
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

if user_input is not None:

    user_input = user_input.strip()

    if not user_input and not uploaded_files:
        st.stop()

    attachment_info = ""

    if uploaded_files:

        attachment_info = (
            "\n\nAttached files:\n"
            + "\n".join(
                f"- {file.name}"
                for file in uploaded_files
            )
        )

    display_message = (
        user_input
        or "Please analyze my attached files."
    )

    if attachment_info:
        display_message += attachment_info

    # Save user message once.

    st.session_state.messages.append({
        "role": "user",
        "content": display_message
    })

    saved = save_message(
        "user",
        display_message
    )

    with st.chat_message("user"):

        st.markdown(display_message)

    if not saved and supabase is not None:

        st.warning(
            "Your message could not be saved to Supabase."
        )

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

            with st.spinner("FAHIM AI is processing your request..."):

                for event in generate_response(
                    user_input or "Analyze the attached files.",
                    uploaded_files
                ):

                    if event["type"] == "token":

                        full_response += event["text"]

                        selected_provider = event["provider"]
                        selected_model = event["model"]

                        response_placeholder.markdown(
                            full_response
                        )

                    elif event["type"] == "done":

                        selected_provider = event["provider"]
                        selected_model = event["model"]

            response_placeholder.markdown(
                full_response
            )

            st.session_state.active_provider = selected_provider
            st.session_state.active_model = selected_model
            st.session_state.last_error = None

            provider_placeholder.caption(
                f"⚡ Provider: {selected_provider} | "
                f"Model: {selected_model}"
            )

            # Save successful assistant response.

            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response
            })

            assistant_saved = save_message(
                "assistant",
                full_response
            )

            if not assistant_saved and supabase is not None:

                st.warning(
                    "The answer was generated, but saving it "
                    "to Supabase failed."
                )

        except Exception as error:

            error_message = str(error)

            st.session_state.last_error = error_message

            st.session_state.active_provider = "Failed"
            st.session_state.active_model = "None"

            st.error(
                "AI request failed. All available providers "
                "may be unavailable or incorrectly configured."
            )

            with st.expander("Technical error details"):

                st.code(error_message)


# ============================================================
# 22. FOOTER
# ============================================================

st.divider()

st.caption(
    f"FAHIM AI v{APP_VERSION} | "
    "Hybrid Multimodal AI Assistant | "
    "Powered by Fahim"
)
