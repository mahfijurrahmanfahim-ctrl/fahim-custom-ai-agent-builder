
# ================================================================
# FAHIM AI v6.0 - FULL REBUILT EDITION
# Hybrid Multi-Provider AI Assistant
#
# NaraRouter + Gemini + Groq + OpenRouter
# Supabase Persistent Chat History
# Web Search + Image Search
# Multiple Image / Audio / PDF / Text Uploads
# Automatic Model Discovery
# Free-model-first provider routing
# Quota and API error handling
#
# Existing Supabase table is preserved:
# chat_history(session_id, role, content, created_at)
# ================================================================

import streamlit as st
import requests
import json
import time
import uuid
import mimetypes
import traceback

from datetime import datetime, timezone

# ================================================================
# OPTIONAL LIBRARIES
# ================================================================

try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except Exception:
    SUPABASE_AVAILABLE = False

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except Exception:
    DDGS_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

try:
    from pypdf import PdfReader
    from io import BytesIO
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False


# ================================================================
# PAGE CONFIGURATION
# ================================================================

st.set_page_config(
    page_title="FAHIM AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ================================================================
# APPLICATION CONSTANTS
# ================================================================

APP_NAME = "FAHIM AI"
APP_VERSION = "6.1"

NARA_BASE_URL = "https://router.bynara.id/v1"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"

SYSTEM_PROMPT = """
You are FAHIM AI, a helpful hybrid multimodal AI assistant.

Your responsibilities:
- Answer accurately and clearly.
- Support English and Bengali.
- Explain technical subjects step by step.
- Help with Python, Streamlit, AI, graphic design and business.
- Analyse supplied documents and supported media.
- Never invent facts, prices, links or search results.
- Clearly explain uncertainty.
- Do not claim to have viewed an image or file unless it
  was actually supplied to a model that supports it.
"""


# ================================================================
# SECRET MANAGEMENT
# ================================================================

def get_secret(name, default=""):
    try:
        value = st.secrets.get(name, default)
        return str(value).strip() if value else default
    except Exception:
        return default


NARA_API_KEY = get_secret("NARA_API_KEY")
GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
GROQ_API_KEY = get_secret("GROQ_API_KEY")
OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY")
CLAUDE_API_KEY = (
    get_secret("ANTHROPIC_API_KEY")
    or get_secret("CLAUDE_API_KEY")
)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")

GEMINI_MODEL = get_secret(
    "GEMINI_MODEL",
    DEFAULT_GEMINI_MODEL
)

NARA_MODEL_SETTING = get_secret(
    "NARA_MODEL",
    ""
)

GROQ_MODEL_SETTING = get_secret(
    "GROQ_MODEL",
    ""
)

OPENROUTER_MODEL_SETTING = get_secret(
    "OPENROUTER_MODEL",
    ""
)

CLAUDE_MODEL_SETTING = get_secret(
    "CLAUDE_MODEL",
    ""
)

DEFAULT_CLAUDE_MODEL = "claude-sonnet-5-5"


# ================================================================
# SESSION STATE
# ================================================================

def initialize_state():

    defaults = {
        "session_id": str(uuid.uuid4()),
        "messages": [],
        "provider": "Auto",
        "last_provider": None,
        "last_model": None,
        "nara_models": [],
        "groq_models": [],
        "openrouter_models": [],
        "claude_models": [],
        "provider_errors": [],
        "gemini_quota_blocked": False,
        "web_search_enabled": False,
        "image_search_enabled": False,
        "show_settings": False,
        "history_loaded": False,
        "input_counter": 0
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_state()


# ================================================================
# SUPABASE CONNECTION
# ================================================================

@st.cache_resource(show_spinner=False)
def get_supabase_client(url, key):

    if not SUPABASE_AVAILABLE:
        return None

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None


supabase = get_supabase_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ================================================================
# DATABASE FUNCTIONS
# ================================================================

def save_message(role, content):

    if not supabase:
        return False

    try:

        record = {
            "session_id": st.session_state.session_id,
            "role": role,
            "content": str(content)
        }

        supabase.table("chat_history").insert(
            record
        ).execute()

        return True

    except Exception as error:

        st.warning(
            "Chat could not be saved to Supabase: "
            + str(error)
        )

        return False


def load_chat_history():

    if not supabase:
        return []

    try:

        response = (
            supabase.table("chat_history")
            .select("role,content,created_at")
            .eq(
                "session_id",
                st.session_state.session_id
            )
            .order("created_at")
            .limit(100)
            .execute()
        )

        return response.data or []

    except Exception as error:

        st.warning(
            "Could not load chat history: "
            + str(error)
        )

        return []


def initialize_chat_history():

    if st.session_state.history_loaded:
        return

    rows = load_chat_history()

    if rows:

        st.session_state.messages = [
            {
                "role": row["role"],
                "content": row["content"]
            }
            for row in rows
            if row.get("role") in ("user", "assistant")
        ]

    st.session_state.history_loaded = True


initialize_chat_history()


# ================================================================
# API RESPONSE HELPERS
# ================================================================

def extract_error(response):

    try:
        data = response.json()

        if isinstance(data, dict):

            error = data.get("error", data)

            if isinstance(error, dict):
                return str(
                    error.get("message")
                    or error.get("detail")
                    or error
                )

            return str(error)

        return str(data)

    except Exception:
        return response.text[:1000]


def extract_chat_text(data):

    try:

        choices = data.get("choices", [])

        if not choices:
            raise ValueError("No choices returned by provider.")

        message = choices[0].get("message", {})

        content = message.get("content", "")

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):

            parts = []

            for item in content:

                if isinstance(item, dict):
                    text = item.get("text")

                    if text:
                        parts.append(text)

            return "\n".join(parts).strip()

        return str(content).strip()

    except Exception as error:
        raise RuntimeError(
            "Invalid AI response: " + str(error)
        )


# ================================================================
# NARAROUTER MODEL DISCOVERY
# ================================================================

def discover_nara_models():

    if not NARA_API_KEY:
        return []

    try:

        response = requests.get(
            NARA_BASE_URL + "/models",
            headers={
                "Authorization": (
                    "Bearer " + NARA_API_KEY
                )
            },
            timeout=15
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Nara model discovery failed: "
                + extract_error(response)
            )

        data = response.json()

        models = data.get("data", [])

        result = []

        for item in models:

            if isinstance(item, dict):

                model_id = item.get("id")

                if model_id:
                    result.append(model_id)

        st.session_state.nara_models = result

        return result

    except Exception as error:

        st.session_state.provider_errors.append(
            "Nara model discovery: " + str(error)
        )

        return []


def choose_nara_model(models):

    if NARA_MODEL_SETTING:
        if NARA_MODEL_SETTING in models:
            return NARA_MODEL_SETTING

    if not models:
        return None

    # Prefer the free model explicitly shown on the
    # user's NaraRouter Free plan.
    preferences = [
        "laguna-s-2.1",
        "Laguna S 2.1",
        "auto/bynara"
    ]

    for preferred in preferences:

        for model in models:

            if model.lower() == preferred.lower():
                return model

    # The authenticated model list is the authority
    # for models available to this API key.
    return models[0]


# ================================================================
# NARAROUTER TEXT REQUEST
# ================================================================

def generate_nara(messages):

    if not NARA_API_KEY:
        raise RuntimeError("NARA_API_KEY is missing.")

    models = discover_nara_models()

    model = choose_nara_model(models)

    if not model:

        raise RuntimeError(
            "NaraRouter returned no available models. "
            "Check your API key and /v1/models access."
        )

    # Minimal payload:
    # no unsupported temperature,
    # no response_format,
    # no tools,
    # no image or audio payload.
    payload = {
        "model": model,
        "messages": messages
    }

    response = requests.post(
        NARA_BASE_URL + "/chat/completions",
        headers={
            "Authorization": (
                "Bearer " + NARA_API_KEY
            ),
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=60
    )

    if response.status_code != 200:

        raise RuntimeError(
            "NaraRouter HTTP "
            + str(response.status_code)
            + ": "
            + extract_error(response)
        )

    answer = extract_chat_text(response.json())

    if not answer:
        raise RuntimeError(
            "NaraRouter returned an empty response."
        )

    return answer, model


# ================================================================
# GROQ MODEL DISCOVERY
# ================================================================

def discover_groq_models():

    if not GROQ_API_KEY:
        return []

    try:

        response = requests.get(
            GROQ_BASE_URL + "/models",
            headers={
                "Authorization": (
                    "Bearer " + GROQ_API_KEY
                )
            },
            timeout=15
        )

        if response.status_code != 200:
            raise RuntimeError(extract_error(response))

        data = response.json()

        result = []

        for item in data.get("data", []):

            model_id = item.get("id")

            if not model_id:
                continue

            lowered = model_id.lower()

            excluded = (
                "whisper",
                "embedding",
                "speech",
                "guard",
                "moderation"
            )

            if any(word in lowered for word in excluded):
                continue

            result.append(model_id)

        st.session_state.groq_models = result

        return result

    except Exception as error:

        st.session_state.provider_errors.append(
            "Groq model discovery: " + str(error)
        )

        return []


def choose_groq_model(models):

    if GROQ_MODEL_SETTING:
        if GROQ_MODEL_SETTING in models:
            return GROQ_MODEL_SETTING

    preferences = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant"
    ]

    for preferred in preferences:

        if preferred in models:
            return preferred

    return models[0] if models else None


# ================================================================
# GROQ TEXT REQUEST
# ================================================================

def generate_groq(messages):

    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing.")

    models = discover_groq_models()

    model = choose_groq_model(models)

    if not model:
        raise RuntimeError(
            "No accessible Groq chat model was found."
        )

    payload = {
        "model": model,
        "messages": messages
    }

    response = requests.post(
        GROQ_BASE_URL + "/chat/completions",
        headers={
            "Authorization": (
                "Bearer " + GROQ_API_KEY
            ),
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=45
    )

    if response.status_code != 200:

        raise RuntimeError(
            "Groq HTTP "
            + str(response.status_code)
            + ": "
            + extract_error(response)
        )

    answer = extract_chat_text(response.json())

    if not answer:
        raise RuntimeError("Groq returned an empty answer.")

    return answer, model


# ================================================================
# OPENROUTER FREE MODEL DISCOVERY
# ================================================================

def discover_openrouter_models():

    if not OPENROUTER_API_KEY:
        return []

    try:

        response = requests.get(
            OPENROUTER_BASE_URL + "/models",
            headers={
                "Authorization": (
                    "Bearer " + OPENROUTER_API_KEY
                )
            },
            timeout=20
        )

        if response.status_code != 200:
            raise RuntimeError(extract_error(response))

        data = response.json()

        free_models = []

        for item in data.get("data", []):

            model_id = item.get("id")

            pricing = item.get("pricing", {})

            if not model_id:
                continue

            prompt_price = str(
                pricing.get("prompt", "")
            )

            completion_price = str(
                pricing.get("completion", "")
            )

            try:

                if (
                    float(prompt_price) == 0
                    and float(completion_price) == 0
                ):
                    free_models.append(model_id)

            except Exception:
                continue

        st.session_state.openrouter_models = free_models

        return free_models

    except Exception as error:

        st.session_state.provider_errors.append(
            "OpenRouter model discovery: " + str(error)
        )

        return []


def choose_openrouter_model(models):

    if OPENROUTER_MODEL_SETTING:
        if OPENROUTER_MODEL_SETTING in models:
            return OPENROUTER_MODEL_SETTING

    if not models:
        return None

    # Prefer Laguna if the exact free endpoint is listed.
    for model in models:

        if "laguna-s-2.1" in model.lower():
            return model

    return models[0]


# ================================================================
# OPENROUTER TEXT REQUEST
# ================================================================

def generate_openrouter(messages):

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing."
        )

    models = discover_openrouter_models()

    model = choose_openrouter_model(models)

    if not model:
        raise RuntimeError(
            "No zero-price OpenRouter model was found."
        )

    response = requests.post(
        OPENROUTER_BASE_URL + "/chat/completions",
        headers={
            "Authorization": (
                "Bearer " + OPENROUTER_API_KEY
            ),
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": messages
        },
        timeout=60
    )

    if response.status_code != 200:

        raise RuntimeError(
            "OpenRouter HTTP "
            + str(response.status_code)
            + ": "
            + extract_error(response)
        )

    answer = extract_chat_text(response.json())

    if not answer:
        raise RuntimeError(
            "OpenRouter returned an empty response."
        )

    return answer, model


# ================================================================
# CLAUDE MODEL DISCOVERY AND TEXT REQUEST
# ================================================================

def discover_claude_models():

    if not CLAUDE_API_KEY:
        return []

    try:

        response = requests.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            timeout=20
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Claude model discovery HTTP "
                + str(response.status_code)
                + ": "
                + extract_error(response)
            )

        data = response.json()
        models = [
            item.get("id")
            for item in data.get("data", [])
            if isinstance(item, dict) and item.get("id")
        ]

        st.session_state.claude_models = models
        return models

    except Exception as error:

        st.session_state.provider_errors.append(
            "Claude model discovery: " + str(error)
        )
        return []


def choose_claude_model(models):

    if CLAUDE_MODEL_SETTING:
        if CLAUDE_MODEL_SETTING in models:
            return CLAUDE_MODEL_SETTING

    if DEFAULT_CLAUDE_MODEL in models:
        return DEFAULT_CLAUDE_MODEL

    return models[0] if models else None


def generate_claude(messages):

    if not CLAUDE_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is missing from Streamlit Secrets."
        )

    models = discover_claude_models()
    model = choose_claude_model(models)

    if not model:
        raise RuntimeError(
            "Claude returned no available models. "
            "Check the API key, account access, and API billing."
        )

    system_parts = []
    conversation = []

    for item in messages:

        role = item.get("role")
        content = item.get("content", "")

        if role == "system":
            if content:
                system_parts.append(str(content))
        elif role in ("user", "assistant"):
            conversation.append({
                "role": role,
                "content": str(content)
            })

    if not conversation:
        raise RuntimeError("Claude request has no user messages.")

    payload = {
        "model": model,
        "max_tokens": 2048,
        "messages": conversation
    }

    if system_parts:
        payload["system"] = "\n\n".join(system_parts)

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json=payload,
        timeout=90
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Claude API HTTP "
            + str(response.status_code)
            + ": "
            + extract_error(response)
        )

    data = response.json()
    answer = "\n".join(
        block.get("text", "")
        for block in data.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ).strip()

    if not answer:
        raise RuntimeError("Claude returned an empty response.")

    return answer, model


# ================================================================
# GEMINI MULTIMODAL REQUEST
# ================================================================

def generate_gemini(prompt, uploaded_files=None):

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    if not GEMINI_AVAILABLE:
        raise RuntimeError(
            "Install google-genai to use Gemini."
        )

    if st.session_state.gemini_quota_blocked:
        raise RuntimeError(
            "Gemini is temporarily disabled because "
            "its free daily quota was exhausted."
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    contents = [prompt]

    for uploaded in uploaded_files or []:

        file_bytes = uploaded.getvalue()

        mime_type = (
            uploaded.type
            or mimetypes.guess_type(uploaded.name)[0]
            or "application/octet-stream"
        )

        supported = (
            mime_type.startswith("image/")
            or mime_type.startswith("audio/")
            or mime_type == "application/pdf"
        )

        if not supported:

            raise RuntimeError(
                "Gemini attachment type is not supported: "
                + uploaded.name
            )

        contents.append(
            types.Part.from_bytes(
                data=file_bytes,
                mime_type=mime_type
            )
        )

    try:

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents
        )

        answer = response.text or ""

        if not answer.strip():
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        return answer.strip(), GEMINI_MODEL

    except Exception as error:

        message = str(error)

        if (
            "429" in message
            or "RESOURCE_EXHAUSTED" in message
            or "quota" in message.lower()
        ):

            st.session_state.gemini_quota_blocked = True

        raise RuntimeError(
            "Gemini: " + message
        )


# ================================================================
# FILE TEXT EXTRACTION
# ================================================================

def extract_text_from_files(uploaded_files):

    extracted = []

    for uploaded in uploaded_files or []:

        name = uploaded.name.lower()

        mime_type = uploaded.type or ""

        try:

            if (
                mime_type.startswith("text/")
                or name.endswith(".txt")
                or name.endswith(".md")
                or name.endswith(".csv")
                or name.endswith(".json")
                or name.endswith(".py")
            ):

                text = uploaded.getvalue().decode(
                    "utf-8",
                    errors="replace"
                )

                extracted.append(
                    "\n\nFILE: "
                    + uploaded.name
                    + "\n"
                    + text[:25000]
                )

            elif name.endswith(".pdf") and PDF_AVAILABLE:

                reader = PdfReader(
                    BytesIO(uploaded.getvalue())
                )

                pages = []

                for page in reader.pages[:30]:

                    pages.append(
                        page.extract_text() or ""
                    )

                extracted.append(
                    "\n\nPDF: "
                    + uploaded.name
                    + "\n"
                    + "\n".join(pages)[:30000]
                )

        except Exception as error:

            extracted.append(
                "\nCould not extract "
                + uploaded.name
                + ": "
                + str(error)
            )

    return "\n".join(extracted)


# ================================================================
# WEB SEARCH
# ================================================================

@st.cache_data(ttl=300, show_spinner=False)
def search_web(query):

    if not DDGS_AVAILABLE:
        return []

    try:

        with DDGS() as ddgs:

            results = list(
                ddgs.text(
                    query,
                    max_results=5
                )
            )

        cleaned = []

        for item in results:

            cleaned.append({
                "title": item.get("title", ""),
                "url": item.get("href", ""),
                "body": item.get("body", "")
            })

        return cleaned

    except Exception:
        return []


def format_web_results(results):

    if not results:
        return "No web search results were returned."

    output = []

    for index, item in enumerate(results, 1):

        output.append(
            f"{index}. {item['title']}\n"
            f"URL: {item['url']}\n"
            f"Summary: {item['body']}"
        )

    return "\n\n".join(output)


# ================================================================
# IMAGE SEARCH
# ================================================================

@st.cache_data(ttl=300, show_spinner=False)
def search_images(query):

    if not DDGS_AVAILABLE:
        return []

    try:

        with DDGS() as ddgs:

            results = list(
                ddgs.images(
                    query,
                    max_results=8
                )
            )

        cleaned = []

        for item in results:

            image_url = (
                item.get("image")
                or item.get("thumbnail")
                or item.get("url")
            )

            if image_url:

                cleaned.append({
                    "title": item.get("title", query),
                    "image": image_url,
                    "source": item.get("url", "")
                })

        return cleaned

    except Exception:
        return []


# ================================================================
# MESSAGE PREPARATION
# ================================================================

def prepare_messages(user_prompt, web_context=""):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    previous = st.session_state.messages[-12:]

    for item in previous:

        if item["role"] in ("user", "assistant"):

            messages.append({
                "role": item["role"],
                "content": item["content"]
            })

    final_prompt = user_prompt

    if web_context:

        final_prompt += (
            "\n\nLIVE WEB SEARCH RESULTS:\n"
            + web_context
            + "\n\nUse these results as references. "
            "Do not invent additional sources."
        )

    messages.append({
        "role": "user",
        "content": final_prompt
    })

    return messages


# ================================================================
# PROVIDER ROUTING
# ================================================================

def run_text_providers(messages):

    provider_order = [
        ("Claude", generate_claude),
        ("NaraRouter", generate_nara),
        ("Groq", generate_groq),
        ("OpenRouter", generate_openrouter)
    ]

    selected = st.session_state.get("provider", "Auto")

    if selected == "Gemini":

        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is missing.")

        prompt = "\n\n".join(
            item.get("role", "user").upper()
            + ": "
            + str(item.get("content", ""))
            for item in messages
            if item.get("role") in ("system", "user", "assistant")
        )
        answer, model = generate_gemini(prompt)
        st.session_state.last_provider = "Gemini"
        st.session_state.last_model = model
        return answer

    if selected != "Auto":
        provider_order = [
            item for item in provider_order
            if item[0] == selected
        ]

    errors = []

    for provider_name, function in provider_order:

        try:

            if provider_name == "Claude" and not CLAUDE_API_KEY:
                if selected == "Claude":
                    raise RuntimeError(
                        "ANTHROPIC_API_KEY is missing from Streamlit Secrets."
                    )
                continue

            if provider_name == "NaraRouter" and not NARA_API_KEY:
                if selected == "NaraRouter":
                    raise RuntimeError("NARA_API_KEY is missing.")
                continue

            if provider_name == "Groq" and not GROQ_API_KEY:
                if selected == "Groq":
                    raise RuntimeError("GROQ_API_KEY is missing.")
                continue

            if provider_name == "OpenRouter" and not OPENROUTER_API_KEY:
                if selected == "OpenRouter":
                    raise RuntimeError("OPENROUTER_API_KEY is missing.")
                continue

            answer, model = function(messages)

            st.session_state.last_provider = provider_name
            st.session_state.last_model = model

            return answer

        except Exception as error:

            error_text = provider_name + ": " + str(error)
            errors.append(error_text)
            st.session_state.provider_errors.append(error_text)

            if selected != "Auto":
                break

    raise RuntimeError(
        "Selected provider failed or no configured text provider was available:\n\n"
        + ("\n\n".join(errors) if errors else "Add the provider API key in Streamlit Secrets.")
    )


# ================================================================
# MAIN AI REQUEST
# ================================================================

def process_ai_request(
    prompt,
    uploaded_files=None,
    use_web=False
):

    uploaded_files = uploaded_files or []

    web_context = ""

    # Search happens before AI generation so the
    # retrieved results can be included in the prompt.
    if use_web:

        with st.spinner("Searching the web..."):

            results = search_web(prompt)

        web_context = format_web_results(results)

        if not results:

            st.info(
                "Web search returned no results. "
                "The AI will answer without live search."
            )

    extracted_text = extract_text_from_files(
        uploaded_files
    )

    complete_prompt = prompt

    if extracted_text:

        complete_prompt += (
            "\n\nEXTRACTED FILE CONTENT:\n"
            + extracted_text
        )

    # If images or audio are uploaded, use Gemini's
    # multimodal endpoint. Nara Laguna text requests
    # must not receive unsupported image payloads.
    multimodal_files = []

    for uploaded in uploaded_files:

        mime_type = uploaded.type or ""

        if (
            mime_type.startswith("image/")
            or mime_type.startswith("audio/")
            or mime_type == "application/pdf"
        ):

            multimodal_files.append(uploaded)

    if multimodal_files:

        if not GEMINI_API_KEY:

            raise RuntimeError(
                "Image/audio/PDF understanding requires "
                "a configured multimodal provider. "
                "Nara Laguna is not used for this upload."
            )

        if web_context:

            complete_prompt += (
                "\n\nWEB SEARCH RESULTS:\n"
                + web_context
            )

        answer, model = generate_gemini(
            complete_prompt,
            multimodal_files
        )

        st.session_state.last_provider = "Gemini"
        st.session_state.last_model = model

        return answer

    messages = prepare_messages(
        complete_prompt,
        web_context
    )

    return run_text_providers(messages)


# ================================================================
# CONNECTION TESTS
# ================================================================

def test_nara_connection():

    if not NARA_API_KEY:
        return False, "NARA_API_KEY is missing."

    try:

        answer, model = generate_nara([
            {
                "role": "user",
                "content": "Reply with exactly: NARA CONNECTION SUCCESSFUL"
            }
        ])

        return True, (
            "NARA CONNECTION SUCCESSFUL\n"
            "Model: " + model + "\n"
            + answer
        )

    except Exception as error:

        return False, str(error)


def test_groq_connection():

    if not GROQ_API_KEY:
        return False, "GROQ_API_KEY is missing."

    try:

        answer, model = generate_groq([
            {
                "role": "user",
                "content": "Reply with exactly: GROQ CONNECTION SUCCESSFUL"
            }
        ])

        return True, (
            "GROQ CONNECTION SUCCESSFUL\n"
            "Model: " + model + "\n"
            + answer
        )

    except Exception as error:

        return False, str(error)


def test_claude_connection():

    if not CLAUDE_API_KEY:
        return False, (
            "ANTHROPIC_API_KEY is missing from Streamlit Secrets."
        )

    try:

        answer, model = generate_claude([
            {
                "role": "user",
                "content": "Reply with exactly: CLAUDE CONNECTION SUCCESSFUL"
            }
        ])

        return True, (
            "CLAUDE CONNECTION SUCCESSFUL\n"
            "Model: " + model + "\n"
            + answer
        )

    except Exception as error:

        return False, str(error)


def test_gemini_connection():

    if not GEMINI_API_KEY:
        return False, "GEMINI_API_KEY is missing."

    if st.session_state.gemini_quota_blocked:
        return False, "Gemini quota was previously exhausted."

    try:

        answer, model = generate_gemini(
            "Reply with exactly: GEMINI CONNECTION SUCCESSFUL"
        )

        return True, (
            "GEMINI CONNECTION SUCCESSFUL\n"
            "Model: " + model + "\n"
            + answer
        )

    except Exception as error:

        return False, str(error)


# ================================================================
# PREMIUM INTERFACE STYLING
# ================================================================

st.markdown(
    """
    <style>
    :root {
        --fahim-accent: #a78bfa;
        --fahim-accent-2: #60a5fa;
        --fahim-surface: rgba(255,255,255,0.045);
        --fahim-border: rgba(148,163,184,0.18);
    }
    .stApp {
        background:
            radial-gradient(ellipse at 12% 0%, rgba(99,102,241,.13), transparent 34%),
            radial-gradient(ellipse at 88% 8%, rgba(14,165,233,.09), transparent 30%);
    }
    [data-testid="stHeader"] {
        background: rgba(8, 12, 25, .72);
        backdrop-filter: blur(14px);
    }
    [data-testid="stSidebar"] {
        border-right: 1px solid var(--fahim-border);
        background: rgba(9, 14, 29, .92);
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.25rem;
    }
    .block-container {
        max-width: 1120px;
        padding-top: 2.1rem;
        padding-bottom: 3rem;
    }
    .fahim-brand {
        display:flex; align-items:center; gap:12px;
        padding: 12px 4px 18px;
    }
    .fahim-brand-icon {
        width:44px; height:44px; border-radius:15px;
        display:grid; place-items:center; font-size:23px;
        color:white;
        background:linear-gradient(135deg,#7c3aed,#2563eb);
        box-shadow:0 8px 28px rgba(99,102,241,.28);
    }
    .fahim-brand-name {font-size:20px;font-weight:800;letter-spacing:.4px;}
    .fahim-brand-sub {font-size:11px;opacity:.62;margin-top:2px;}
    .fahim-hero {
        position:relative; overflow:hidden;
        padding:25px 28px; border-radius:22px;
        border:1px solid rgba(167,139,250,.25);
        background:linear-gradient(115deg,rgba(91,33,182,.24),rgba(30,64,175,.16) 55%,rgba(14,165,233,.10));
        box-shadow:0 16px 50px rgba(0,0,0,.12);
        margin-bottom:18px;
    }
    .fahim-hero:after {
        content:""; position:absolute; width:230px;height:230px;
        right:-85px;top:-135px;border-radius:50%;
        background:rgba(129,140,248,.16);filter:blur(8px);
    }
    .fahim-kicker {
        font-size:11px;letter-spacing:2px;text-transform:uppercase;
        color:#c4b5fd;font-weight:800;margin-bottom:8px;
    }
    .fahim-hero h1 {font-size:clamp(28px,4vw,40px);line-height:1.1;margin:0 0 9px;font-weight:850;}
    .fahim-hero p {font-size:14px;opacity:.76;margin:0;max-width:650px;}
    div[data-testid="stChatMessage"] {
        border:1px solid var(--fahim-border);
        border-radius:18px; padding:14px 16px;
        background:var(--fahim-surface); margin-bottom:12px;
    }
    [data-testid="stChatInput"] {
        border:1px solid rgba(167,139,250,.38);
        border-radius:18px;
        box-shadow:0 8px 28px rgba(0,0,0,.10);
    }
    [data-testid="stFileUploader"] section {
        border:1px dashed rgba(167,139,250,.4);
        border-radius:16px; background:rgba(139,92,246,.045);
    }
    .stButton > button {
        border-radius:12px; font-weight:650;
        transition:all .18s ease;
    }
    .stButton > button:hover {
        border-color:#a78bfa; transform:translateY(-1px);
        box-shadow:0 5px 18px rgba(124,58,237,.14);
    }
    [data-testid="stMetric"] {
        border:1px solid var(--fahim-border);
        padding:12px 14px; border-radius:14px;
        background:var(--fahim-surface);
    }
    @media (max-width: 700px) {
        .block-container {padding:1rem .8rem 2rem;}
        .fahim-hero {padding:20px 18px;border-radius:17px;}
        div[data-testid="stChatMessage"] {padding:11px;border-radius:15px;}
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ================================================================
# SIDEBAR
# ================================================================

with st.sidebar:

    st.markdown(
        """
        <div class="fahim-brand">
          <div class="fahim-brand-icon">✦</div>
          <div>
            <div class="fahim-brand-name">FAHIM AI</div>
            <div class="fahim-brand-sub">PERSONAL AI WORKSPACE · v6.1</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption("Your multi-model assistant")

    st.divider()

    st.subheader("⚙️ Provider Settings")

    provider_choice = st.selectbox(
        "AI provider",
        [
            "Auto",
            "NaraRouter",
            "Groq",
            "OpenRouter",
            "Gemini",
            "Claude"
        ],
        index=0
    )

    st.session_state.provider = provider_choice

    st.divider()

    st.subheader("🔌 Provider Status")

    st.write(
        "Claude:",
        "Key configured" if CLAUDE_API_KEY else "Not configured"
    )

    st.write(
        "NaraRouter:",
        "Connected key" if NARA_API_KEY else "Not configured"
    )

    st.write(
        "Gemini:",
        "Quota exhausted"
        if st.session_state.gemini_quota_blocked
        else (
            "Connected key"
            if GEMINI_API_KEY
            else "Not configured"
        )
    )

    st.write(
        "Groq:",
        "Connected key" if GROQ_API_KEY else "Not configured"
    )

    st.write(
        "OpenRouter:",
        "Connected key"
        if OPENROUTER_API_KEY
        else "Not configured"
    )

    st.divider()

    st.subheader("🔎 Search Settings")

    web_enabled = st.checkbox(
        "Enable web search",
        value=st.session_state.web_search_enabled
    )

    st.session_state.web_search_enabled = web_enabled

    image_enabled = st.checkbox(
        "Enable image search",
        value=st.session_state.image_search_enabled
    )

    st.session_state.image_search_enabled = image_enabled

    st.divider()

    st.subheader("🧪 Connection Tests")

    if st.button(
        "Test Claude",
        use_container_width=True
    ):

        with st.spinner("Testing Claude API..."):

            ok, message = test_claude_connection()

        if ok:
            st.success(message)
        else:
            st.error(message)

    if st.button(
        "Test NaraRouter",
        use_container_width=True
    ):

        with st.spinner("Testing NaraRouter..."):

            ok, message = test_nara_connection()

        if ok:
            st.success(message)
        else:
            st.error(message)

    if st.button(
        "Test Groq",
        use_container_width=True
    ):

        with st.spinner("Testing Groq..."):

            ok, message = test_groq_connection()

        if ok:
            st.success(message)
        else:
            st.error(message)

    if st.button(
        "Test Gemini",
        use_container_width=True
    ):

        with st.spinner("Testing Gemini..."):

            ok, message = test_gemini_connection()

        if ok:
            st.success(message)
        else:
            st.error(message)

    if st.button(
        "Refresh provider models",
        use_container_width=True
    ):

        with st.spinner("Checking available models..."):

            claude = discover_claude_models()
            nara = discover_nara_models()
            groq = discover_groq_models()
            openrouter = discover_openrouter_models()

        st.success("Model discovery completed.")

        st.write("Claude:", claude)
        st.write("NaraRouter:", nara)
        st.write("Groq:", groq)
        st.write("OpenRouter free:", openrouter)

    if st.session_state.gemini_quota_blocked:

        st.warning(
            "Gemini free quota was exhausted. "
            "The app will not repeatedly retry it."
        )

        if st.button(
            "Allow Gemini retry",
            use_container_width=True
        ):

            st.session_state.gemini_quota_blocked = False

            st.rerun()

    st.divider()

    st.subheader("💾 Chat History")

    st.caption(
        "Supabase: "
        + (
            "Connected"
            if supabase
            else "Not configured"
        )
    )

    if st.button(
        "Start New Chat",
        use_container_width=True
    ):

        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.history_loaded = True

        st.rerun()

    st.caption(
        "Starting a new chat does not delete previous "
        "Supabase records."
    )

    if st.button(
        "Clear current screen",
        use_container_width=True
    ):

        st.session_state.messages = []
        st.rerun()


# ================================================================
# MAIN HEADER
# ================================================================

st.markdown(
    """
    <section class="fahim-hero">
      <div class="fahim-kicker">Your personal AI workspace</div>
      <h1>Meet your smarter assistant.</h1>
      <p>One workspace for conversations, research, documents and creative work — powered by your connected AI models.</p>
    </section>
    """,
    unsafe_allow_html=True
)

status_cols = st.columns(4)
status_items = [
    ("AI providers", "Multi-model"),
    ("Capabilities", "Text + files"),
    ("Research", "Web search"),
    ("Workspace", "Chat session")
]
for column, item in zip(status_cols, status_items):
    with column:
        st.metric(item[0], item[1])

if st.session_state.last_provider:

    st.caption(
        "Last successful provider: "
        + str(st.session_state.last_provider)
        + " | Model: "
        + str(st.session_state.last_model)
    )

st.divider()


# ================================================================
# IMAGE SEARCH INTERFACE
# ================================================================

if st.session_state.image_search_enabled:

    with st.expander(
        "🖼️ Image Search",
        expanded=False
    ):

        image_query = st.text_input(
            "Search for images",
            key="image_search_query"
        )

        if st.button("Search Images"):

            if image_query.strip():

                with st.spinner("Finding images..."):

                    image_results = search_images(
                        image_query
                    )

                if image_results:

                    columns = st.columns(2)

                    for index, item in enumerate(image_results):

                        with columns[index % 2]:

                            try:

                                st.image(
                                    item["image"],
                                    caption=item["title"],
                                    use_container_width=True
                                )

                                if item["source"]:
                                    st.markdown(
                                        "[Open source]("
                                        + item["source"]
                                        + ")"
                                    )

                            except Exception:
                                st.caption(
                                    "Image could not be displayed."
                                )

                else:

                    st.info(
                        "No image results found. "
                        "The image search provider may be rate-limited."
                    )


# ================================================================
# DISPLAY CHAT HISTORY
# ================================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ================================================================
# FILE UPLOADS
# ================================================================

uploaded_files = st.file_uploader(
    "📎 Attach images, audio, PDFs or text files",
    type=[
        "png",
        "jpg",
        "jpeg",
        "webp",
        "gif",
        "mp3",
        "wav",
        "m4a",
        "ogg",
        "pdf",
        "txt",
        "md",
        "csv",
        "json",
        "py"
    ],
    accept_multiple_files=True,
    key="fahim_file_uploader"
)

if uploaded_files:

    st.caption(
        str(len(uploaded_files))
        + " file(s) attached"
    )

    for uploaded in uploaded_files:

        st.write(
            "📄 "
            + uploaded.name
            + " — "
            + str(round(uploaded.size / 1024, 1))
            + " KB"
        )


# ================================================================
# CHAT INPUT
# ================================================================

user_prompt = st.chat_input(
    "Message FAHIM AI..."
)


# ================================================================
# CHAT PROCESSING
# ================================================================

if user_prompt:

    prompt = user_prompt.strip()

    if prompt:

        user_display = prompt

        if uploaded_files:

            user_display += (
                "\n\nAttached files: "
                + ", ".join(
                    item.name for item in uploaded_files
                )
            )

        # Save user message to session and database.
        user_message = {
            "role": "user",
            "content": user_display
        }

        st.session_state.messages.append(
            user_message
        )

        save_message(
            "user",
            user_display
        )

        with st.chat_message("user"):

            st.markdown(user_display)

        with st.chat_message("assistant"):

            answer_placeholder = st.empty()

            status_placeholder = st.empty()

            try:

                with st.spinner("FAHIM AI is thinking..."):

                    answer = process_ai_request(
                        prompt,
                        uploaded_files,
                        use_web=(
                            st.session_state.web_search_enabled
                        )
                    )

                answer_placeholder.markdown(answer)

                status_placeholder.caption(
                    "⚡ Provider: "
                    + str(st.session_state.last_provider)
                    + " | Model: "
                    + str(st.session_state.last_model)
                )

                assistant_message = {
                    "role": "assistant",
                    "content": answer
                }

                st.session_state.messages.append(
                    assistant_message
                )

                save_message(
                    "assistant",
                    answer
                )

            except Exception as error:

                error_message = str(error)

                answer_placeholder.error(
                    "AI request failed.\n\n"
                    + error_message
                )

                status_placeholder.caption(
                    "Check provider status in Settings."
                )

        # Reset uploader only after processing.
        st.rerun()


# ================================================================
# FOOTER
# ================================================================

st.divider()

footer_left, footer_right = st.columns(2)

with footer_left:

    st.caption(
        "FAHIM AI v"
        + APP_VERSION
        + " | Powered by Fahim"
    )

with footer_right:

    st.caption(
        "Hybrid AI • Free-model-first routing"
    )


# ================================================================
# END OF FAHIM AI v6.0
# ================================================================
