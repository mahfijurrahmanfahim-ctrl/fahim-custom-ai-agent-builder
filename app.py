
import streamlit as st
from transformers import pipeline
from datetime import datetime

# ==========================================
# FAHIM CUSTOM AI AGENT BUILDER PRO
# ==========================================

st.set_page_config(
    page_title="FAHIM CUSTOM AI AGENT BUILDER",
    page_icon="🤖",
    layout="wide"
)

MODEL_ID = "google/flan-t5-small"

# ==========================================
# DEFAULT FAHIM PROFILE
# ==========================================

FAHIM_MASTER_PROFILE = """
Name: Mahfijur Rahman Fahim
Brand: FAHIM GRAPHIC DESIGN
Location: Portugal
Profession: Graphic Designer, AI-Assisted Creative
Designer, Image Editor and Video Content Creator.

Services:
Restaurant Menu Design, Social Media Post Design,
Logo Design, Flyer Design, Poster Design,
Photo Editing, DSLR-Style Image Enhancement,
AI Image Generation and Promotional Video Creation.

Skills:
Canva, ChatGPT, Google Gemini, CapCut,
Google Flow, Graphic Design, Photo Editing,
Video Editing and AI Image Generation.

Design Style:
Premium Luxury Black and Gold.
Realistic imagery, professional lighting,
clean typography and modern presentation.

Tagline:
Creative Design. Professional Results.

Portfolio:
https://mahfijurrahmanfahim-ctrl.github.io/fahim-graphic-design-portfolio/

Fiverr Menu Design:
https://www.fiverr.com/s/X00EVme

Fiverr Social Media Design:
https://www.fiverr.com/s/qbbQr6y

TikTok:
@m.r.fahim

Offer:
First Menu Sample: 100% Free.
New Business Launch Pack: £59.

Target Clients:
Restaurants, Cafes, Gyms, Clothing Brands
and Small Businesses.

Target Markets:
Portugal, United Kingdom and International Clients.
"""

# ==========================================
# LOAD AI MODEL
# ==========================================

@st.cache_resource(show_spinner=False)
def load_ai():
    return pipeline(
        "text2text-generation",
        model=MODEL_ID,
        device=-1
    )


# ==========================================
# TOKEN MANAGEMENT
# ==========================================

def limit_text(text, tokenizer, max_tokens):
    tokens = tokenizer.encode(
        str(text),
        truncation=True,
        max_length=max_tokens
    )

    return tokenizer.decode(
        tokens,
        skip_special_tokens=True
    )


# ==========================================
# AI AGENT ENGINE
# ==========================================

def generate_answer(
    profile,
    assistant_name,
    role,
    language,
    tone,
    instructions,
    question,
    history
):

    ai = load_ai()
    tokenizer = ai.tokenizer

    safe_profile = limit_text(
        profile, tokenizer, 160
    )

    safe_instructions = limit_text(
        instructions, tokenizer, 30
    )

    safe_question = limit_text(
        question, tokenizer, 80
    )

    conversation = ""

    for message in history[-4:]:
        conversation += (
            message["role"] + ": " +
            limit_text(
                message["content"],
                tokenizer,
                20
            ) + "\n"
        )

    prompt = f"""
You are {assistant_name}.

Your role is {role}.
Answer in {language}.
Your communication style is {tone}.

USER PROFILE:
{safe_profile}

SPECIAL INSTRUCTIONS:
{safe_instructions}

RECENT CONVERSATION:
{conversation}

QUESTION:
{safe_question}

Give a helpful and accurate answer.
Use information from the profile.
Do not invent facts.
If information is unavailable, say so.

ANSWER:
"""

    result = ai(
        prompt,
        max_new_tokens=120,
        do_sample=False,
        truncation=True
    )

    return result[0]["generated_text"].strip()


# ==========================================
# HEADER
# ==========================================

st.markdown("""
# 🤖 FAHIM CUSTOM AI AGENT BUILDER PRO

### Build Your Own Personal AI Assistant

Paste your profile, customize your assistant
and start chatting with your own AI agent.
""")

st.caption(
    "Powered by an open-source Hugging Face model."
)

# ==========================================
# SIDEBAR
# ==========================================

st.sidebar.title("⚙️ AGENT SETTINGS")

assistant_name = st.sidebar.text_input(
    "Assistant Name",
    "My Personal AI"
)

role = st.sidebar.text_input(
    "Assistant Role",
    "Personal and Business Assistant"
)

language = st.sidebar.selectbox(
    "Response Language",
    [
        "English",
        "Bengali",
        "Portuguese",
        "Spanish",
        "Hindi",
        "French"
    ]
)

tone = st.sidebar.selectbox(
    "Communication Style",
    [
        "Professional",
        "Friendly",
        "Simple and Clear",
        "Creative",
        "Formal"
    ]
)

instructions = st.sidebar.text_area(
    "Custom Instructions",
    placeholder="Add instructions for your AI assistant..."
)

st.sidebar.divider()

st.sidebar.markdown("### 🌐 FAHIM PORTFOLIO")

st.sidebar.markdown(
    "[Visit Portfolio](https://mahfijurrahmanfahim-ctrl.github.io/fahim-graphic-design-portfolio/)"
)

st.sidebar.markdown(
    "[Fiverr Menu Design](https://www.fiverr.com/s/X00EVme)"
)

st.sidebar.markdown(
    "[Fiverr Social Media Design](https://www.fiverr.com/s/qbbQr6y)"
)

st.sidebar.caption(
    "Model: google/flan-t5-small"
)

# ==========================================
# PROFILE BUILDER
# ==========================================

st.divider()

st.subheader("📁 STEP 1 — CREATE YOUR PROFILE")

st.write(
    "Enter your personal or business information. "
    "Leave the field empty to use Fahim's example profile."
)

profile_data = st.text_area(
    "Your Personal / Business Profile",
    height=250,
    placeholder="""
Name:
Profession:
Business Name:
Location:
Skills:
Services:
Experience:
Website:
Social Media:
Business Goals:
    """
)

active_profile = (
    profile_data.strip()
    if profile_data.strip()
    else FAHIM_MASTER_PROFILE
)

# ==========================================
# CHAT INTERFACE
# ==========================================

st.divider()

st.subheader("💬 STEP 2 — CHAT WITH YOUR AI AGENT")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

col1, col2 = st.columns([3, 1])

with col1:
    st.write(
        f"Assistant: **{assistant_name}**"
    )

with col2:
    if st.button(
        "🗑️ Clear Conversation",
        use_container_width=True
    ):
        st.session_state.chat_history = []
        st.rerun()

# ==========================================
# DISPLAY CHAT HISTORY
# ==========================================

for message in st.session_state.chat_history:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==========================================
# USER INPUT AND AI RESPONSE
# ==========================================

question = st.chat_input(
    "Ask your AI assistant anything..."
)

if question:

    previous_history = (
        st.session_state.chat_history.copy()
    )

    st.session_state.chat_history.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):

        try:

            with st.spinner(
                "🤖 AI assistant is thinking..."
            ):

                response = generate_answer(
                    profile=active_profile,
                    assistant_name=assistant_name,
                    role=role,
                    language=language,
                    tone=tone,
                    instructions=instructions,
                    question=question,
                    history=previous_history
                )

            st.markdown(response)

            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response
            })

        except Exception as error:

            st.error(
                f"AI Error: {str(error)}"
            )

            st.info(
                "Please try again or check the deployment logs."
            )

            # Remove failed user message
            st.session_state.chat_history.pop()


# ==========================================
# EXPORT CONVERSATION
# ==========================================

if st.session_state.chat_history:

    conversation = (
        "FAHIM CUSTOM AI AGENT BUILDER\n"
        f"Assistant: {assistant_name}\n"
        f"Exported: {datetime.now().isoformat()}\n"
        + "=" * 45 + "\n\n"
    )

    for message in st.session_state.chat_history:

        conversation += (
            f"{message['role'].upper()}:\n"
            f"{message['content']}\n\n"
        )

    st.download_button(
        label="📥 DOWNLOAD CONVERSATION",
        data=conversation.encode("utf-8"),
        file_name="my_ai_conversation.txt",
        mime="text/plain"
    )


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.markdown("""
### FAHIM CUSTOM AI AGENT BUILDER PRO

**Created by FAHIM GRAPHIC DESIGN**

Creative Design. Professional Results.
""")

st.caption(
    "Open-source AI model | Profile-based assistant | "
    "No paid AI API key required."
)
