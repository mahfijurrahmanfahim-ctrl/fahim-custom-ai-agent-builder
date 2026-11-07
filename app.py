# ============================================================
# FAHIM AI v5.3 - FREE & FAST EDITION
# NaraRouter Laguna + Gemini + Groq
# DDGS Web Search + Image Search
# Supabase Permanent Chat History
# Multimodal Gemini Fallback
# ============================================================

import os
import json
import mimetypes
import uuid
import time

import streamlit as st
from openai import OpenAI
from google import genai
from google.genai import types
from supabase import create_client


# ============================================================
# 1. CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="FAHIM AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_VERSION = "5.3"

NARA_URL = "https://router.bynara.id/v1"
GROQ_URL = "https://api.groq.com/openai/v1"

NARA_FREE_MODEL = "laguna-s-2.1"
GEMINI_MODEL = "gemini-3.8-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"

MAX_HISTORY = 20
SEARCH_LIMIT = 6


# ============================================================
# 2. SECRETS
# ============================================================

def secret(name, default=""):
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = os.getenv(name, default)

    return default if value is None else str(value).strip()


NARA_KEY = secret("NARA_API_KEY")
GEMINI_KEY = secret("GEMINI_API_KEY")
GROQ_KEY = secret("GROQ_API_KEY")

SUPABASE_URL = secret("SUPABASE_URL")
SUPABASE_KEY = (
    secret("SUPABASE_SECRET_KEY")
    or secret("SUPABASE_KEY")
)


# ============================================================
# 3. SESSION STATE
# ============================================================

defaults = {
    "session_id": str(uuid.uuid4()),
    "messages": [],
    "history_loaded": False,
    "active_provider": "Not connected",
    "active_model": "None",
    "request_count": 0,
    "fallback_count": 0,
    "last_error": None,
    "confirm_clear": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# 4. SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are FAHIM AI, a multilingual AI assistant created by Fahim.

Languages: English and Bengali.

Capabilities:
- Conversation
- Coding
- Technical assistance
- Image understanding
- Audio understanding
- Document understanding
- Web search result analysis

Rules:
- Never invent information.
- Never invent search results.
- Use provided search sources for current information.
- Preserve conversation context.
- Answer in the user's language.
- Keep simple answers concise.
"""


# ============================================================
# 5. SUPABASE
# ============================================================

@st.cache_resource(show_spinner=False)
def get_database():

    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        return create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )
    except Exception:
        return None


db = get_database()


def load_history():

    if st.session_state.history_loaded:
        return

    if db is not None:
        try:
            result = (
                db.table("chat_history")
                .select("role, content")
                .eq("session_id", st.session_state.session_id)
                .order("created_at", desc=False)
                .execute()
            )

            st.session_state.messages = [
                {
                    "role": item["role"],
                    "content": item["content"]
                }
                for item in (result.data or [])
                if item.get("role") in ["user", "assistant"]
            ]

        except Exception as error:
            st.session_state.last_error = str(error)

    st.session_state.history_loaded = True


def save_message(role, content):

    if db is None:
        return False

    try:
        db.table("chat_history").insert({
            "session_id": st.session_state.session_id,
            "role": role,
            "content": str(content)
        }).execute()

        return True

    except Exception as error:
        st.session_state.last_error = str(error)
        return False


def clear_history():

    if db is not None:
        try:
            db.table("chat_history").delete().eq(
                "session_id",
                st.session_state.session_id
            ).execute()

        except Exception as error:
            st.error(str(error))
            return

    st.session_state.messages = []
    st.session_state.history_loaded = True
    st.rerun()


load_history()


# ============================================================
# 6. PROVIDER CLIENTS
# ============================================================

def nara_client():

    if not NARA_KEY:
        raise RuntimeError("NARA_API_KEY missing")

    return OpenAI(
        api_key=NARA_KEY,
        base_url=NARA_URL,
        timeout=30,
        max_retries=0
    )


def groq_client():

    if not GROQ_KEY:
        raise RuntimeError("GROQ_API_KEY missing")

    return OpenAI(
        api_key=GROQ_KEY,
        base_url=GROQ_URL,
        timeout=25,
        max_retries=0
    )


def gemini_client():

    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY missing")

    return genai.Client(
        api_key=GEMINI_KEY,
        http_options=types.HttpOptions(
            timeout=30000
        )
    )


# ============================================================
# 7. CONVERSATION CONTEXT
# ============================================================

def previous_messages():

    messages = st.session_state.messages[:-1]

    return [
        {
            "role": item["role"],
            "content": item["content"]
        }
        for item in messages[-MAX_HISTORY:]
        if item.get("role") in ["user", "assistant"]
    ]


def openai_messages(user_text, search_context=""):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(previous_messages())

    final_text = user_text

    if search_context:
        final_text += (
            "\n\nLIVE WEB SEARCH RESULTS:\n"
            + search_context
        )

    messages.append({
        "role": "user",
        "content": final_text
    })

    return messages


# ============================================================
# 8. FAST WEB SEARCH
# ============================================================

@st.cache_data(ttl=180, show_spinner=False)
def web_search(query):

    try:
        from ddgs import DDGS

        with DDGS() as search:
            results = list(
                search.text(
                    query,
                    max_results=SEARCH_LIMIT
                )
            )

        output = []

        for result in results:
            output.append({
                "title": result.get("title", "Search result"),
                "url": result.get("href", ""),
                "body": result.get("body", "")
            })

        return output, None

    except ImportError:
        return [], "Install ddgs in requirements.txt"

    except Exception as error:
        return [], str(error)


def format_search(results):

    text = []

    for index, item in enumerate(results, 1):

        text.append(
            f"""
Result {index}
Title: {item['title']}
URL: {item['url']}
Information: {item['body']}
"""
        )

    return "\n".join(text)


def needs_search(query):

    keywords = [
        "search online",
        "search web",
        "latest",
        "today",
        "current",
        "news",
        "recent",
        "find online",
        "look up",
        "price today",
        "খুঁজে দেখ",
        "সর্বশেষ",
        "আজকের খবর",
        "বর্তমান",
        "অনলাইনে খুঁজে",
    ]

    query = query.lower()

    return any(word in query for word in keywords)


# ============================================================
# 9. FAST IMAGE SEARCH
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def image_search(query):

    try:
        from ddgs import DDGS

        with DDGS() as search:
            results = list(
                search.images(
                    query,
                    max_results=8
                )
            )

        return results, None

    except Exception as error:
        return [], str(error)


# ============================================================
# 10. GEMINI MULTIMODAL
# ============================================================

def generate_gemini(user_text, files=None, search_context=""):

    client = gemini_client()

    contents = []

    for item in previous_messages():

        contents.append({
            "role": (
                "model"
                if item["role"] == "assistant"
                else "user"
            ),
            "parts": [
                {"text": item["content"]}
            ]
        })

    final_text = SYSTEM_PROMPT + "\n\n" + user_text

    if search_context:
        final_text += (
            "\n\nSEARCH RESULTS:\n"
            + search_context
        )

    parts = [
        types.Part.from_text(text=final_text)
    ]

    for file in files or []:

        mime = (
            file.type
            or mimetypes.guess_type(file.name)[0]
            or "application/octet-stream"
        )

        parts.append(
            types.Part.from_bytes(
                data=file.getvalue(),
                mime_type=mime
            )
        )

    contents.append({
        "role": "user",
        "parts": parts
    })

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.5
        )
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response")

    return response.text, GEMINI_MODEL


# ============================================================
# 11. TEXT GENERATION
# ============================================================

def generate_openai(provider, client, model, messages):

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.5,
        max_tokens=3000
    )

    if not response.choices:
        raise RuntimeError("Empty provider response")

    answer = response.choices[0].message.content

    if not answer:
        raise RuntimeError("Empty response")

    return answer, getattr(response, "model", model)


# ============================================================
# 12. FREE-FIRST FALLBACK
# ============================================================

def generate_answer(user_text, files=None, search_context=""):

    st.session_state.request_count += 1

    # Laguna is text-only: send attachments to Gemini.
    if files:

        answer, model = generate_gemini(
            user_text,
            files,
            search_context
        )

        return answer, "Gemini", model

    messages = openai_messages(
        user_text,
        search_context
    )

    providers = []

    if NARA_KEY:
        providers.append((
            "NaraRouter",
            nara_client,
            NARA_FREE_MODEL
        ))

    if GEMINI_KEY:
        providers.append((
            "Gemini",
            None,
            GEMINI_MODEL
        ))

    if GROQ_KEY:
        providers.append((
            "Groq",
            groq_client,
            GROQ_MODEL
        ))

    if not providers:
        raise RuntimeError("No provider configured")

    errors = []

    for name, factory, model in providers:

        try:

            if name == "Gemini":

                answer, actual_model = generate_gemini(
                    user_text,
                    None,
                    search_context
                )

            else:

                client = factory()

                answer, actual_model = generate_openai(
                    name,
                    client,
                    model,
                    messages
                )

            return answer, name, actual_model

        except Exception as error:

            errors.append(
                f"{name}: {str(error)}"
            )

            st.session_state.fallback_count += 1

    raise RuntimeError(
        "All free providers failed:\n"
        + "\n".join(errors)
    )


# ============================================================
# 13. SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🤖 FAHIM AI")

    st.caption(f"Version {APP_VERSION}")

    st.divider()

    st.subheader("Provider Status")

    st.write(
        "🟢 NaraRouter"
        if NARA_KEY
        else "🔴 NaraRouter missing"
    )

    st.caption(f"Model: {NARA_FREE_MODEL}")

    st.write(
        "🟢 Gemini"
        if GEMINI_KEY
        else "⚪ Gemini"
    )

    st.write(
        "🟢 Groq"
        if GROQ_KEY
        else "⚪ Groq"
    )

    if st.button(
        "Test NaraRouter Connection",
        use_container_width=True
    ):

        try:

            with st.spinner("Testing free model..."):

                answer, provider_model = generate_openai(
                    "NaraRouter",
                    nara_client(),
                    NARA_FREE_MODEL,
                    [
                        {
                            "role": "user",
                            "content": "Reply NARA CONNECTION SUCCESSFUL"
                        }
                    ]
                )

            st.success("NaraRouter connected")
            st.write(answer)
            st.caption(provider_model)

        except Exception as error:
            st.error(str(error))

    st.divider()

    st.subheader("Statistics")

    st.metric(
        "Messages",
        len(st.session_state.messages)
    )

    st.metric(
        "Requests",
        st.session_state.request_count
    )

    st.metric(
        "Fallbacks",
        st.session_state.fallback_count
    )

    st.metric(
        "Active Provider",
        st.session_state.active_provider
    )

    st.metric(
        "Active Model",
        st.session_state.active_model
    )

    st.divider()

    if db:
        st.success("Supabase connected")
    else:
        st.warning("Supabase disconnected")

    if st.button(
        "Export Chat",
        use_container_width=True
    ):

        st.download_button(
            "Download JSON",
            json.dumps(
                st.session_state.messages,
                ensure_ascii=False,
                indent=2
            ),
            "fahim_chat.json",
            "application/json"
        )

    if st.button(
        "Clear Chat",
        use_container_width=True
    ):
        st.session_state.confirm_clear = True

    if st.session_state.confirm_clear:

        if st.button(
            "Confirm Delete",
            type="primary"
        ):
            clear_history()

        if st.button("Cancel"):
            st.session_state.confirm_clear = False
            st.rerun()


# ============================================================
# 14. MAIN INTERFACE
# ============================================================

st.title("🤖 FAHIM AI")

st.caption(
    "Free AI Assistant | NaraRouter + Gemini + Groq"
)

st.divider()


# ============================================================
# 15. IMAGE SEARCH INTERFACE
# ============================================================

with st.expander("🖼️ Image Search"):

    query = st.text_input(
        "Search images",
        key="image_query"
    )

    if st.button("Find Images"):

        if query.strip():

            with st.spinner("Searching images..."):

                results, error = image_search(query)

            if error:
                st.error(error)

            elif results:

                columns = st.columns(2)

                for index, result in enumerate(results):

                    with columns[index % 2]:

                        image_url = result.get("image")

                        if image_url:

                            st.image(
                                image_url,
                                use_container_width=True
                            )

                        st.caption(
                            result.get("title", "Image")
                        )

                        if result.get("url"):
                            st.markdown(
                                f"[Open source]({result['url']})"
                            )

            else:
                st.info("No images found.")


# ============================================================
# 16. CHAT DISPLAY
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ============================================================
# 17. FILE UPLOAD
# ============================================================

st.subheader("📎 Attachments")

files = st.file_uploader(
    "Images, audio and documents",
    type=[
        "jpg", "jpeg", "png", "webp",
        "mp3", "wav", "m4a", "ogg", "flac",
        "pdf", "txt", "md"
    ],
    accept_multiple_files=True,
    key="fahim_files"
)


# ============================================================
# 18. CHAT INPUT
# ============================================================

user_input = st.chat_input("Message FAHIM AI...")


# ============================================================
# 19. PROCESS MESSAGE
# ============================================================

if user_input is not None:

    user_input = user_input.strip()

    if not user_input and not files:
        st.stop()

    display_text = user_input or "Analyze my attachments."

    if files:
        display_text += (
            "\n\nAttachments:\n"
            + "\n".join(
                f"- {file.name}"
                for file in files
            )
        )

    # Save user message once.
    st.session_state.messages.append({
        "role": "user",
        "content": display_text
    })

    saved = save_message(
        "user",
        display_text
    )

    with st.chat_message("user"):
        st.markdown(display_text)

    if not saved and db:
        st.warning("Message could not be saved.")

    # --------------------------------------------------------
    # WEB SEARCH FIRST
    # --------------------------------------------------------

    search_results = []
    search_context = ""

    if needs_search(user_input):

        with st.status(
            "Searching the web...",
            expanded=False
        ) as status:

            search_results, search_error = web_search(
                user_input
            )

            search_context = format_search(
                search_results
            )

            status.update(
                label=(
                    f"Found {len(search_results)} results"
                    if search_results
                    else "No web results"
                ),
                state=(
                    "complete"
                    if search_results
                    else "error"
                )
            )

        if search_results:

            with st.expander(
                "🌐 Web Search Results",
                expanded=True
            ):

                for item in search_results:

                    if item["url"]:
                        st.markdown(
                            f"**[{item['title']}]({item['url']})**"
                        )
                    else:
                        st.write(item["title"])

                    st.write(item["body"])

        elif search_error:
            st.warning(
                "Web search unavailable. Answering without live results."
            )
            st.caption(search_error)

    # --------------------------------------------------------
    # AI GENERATION
    # --------------------------------------------------------

    with st.chat_message("assistant"):

        placeholder = st.empty()

        try:

            with st.spinner("FAHIM AI is thinking..."):

                answer, provider, model = generate_answer(
                    user_input or "Analyze my attachments.",
                    files,
                    search_context
                )

            placeholder.markdown(answer)

            st.session_state.active_provider = provider
            st.session_state.active_model = model
            st.session_state.last_error = None

            st.caption(
                f"⚡ Provider: {provider} | Model: {model}"
            )

            # Save successful response.
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

            if not save_message("assistant", answer) and db:
                st.warning("Answer generated but saving failed.")

        except Exception as error:

            st.session_state.last_error = str(error)
            st.session_state.active_provider = "Failed"
            st.session_state.active_model = "None"

            st.error("AI request failed.")

            with st.expander("Technical details"):
                st.code(str(error))


# ============================================================
# 20. FOOTER
# ============================================================

st.divider()

st.caption(
    f"FAHIM AI v{APP_VERSION} | Powered by Fahim"
)
