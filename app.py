import streamlit as st
import torch
import json
from datetime import datetime
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Fahim Custom AI Agent Builder",
    page_icon="🤖",
    layout="wide"
)

MODEL_NAME = "google/flan-t5-small"

# ==========================================
# 2. LOAD AI MODEL
# ==========================================

@st.cache_resource(show_spinner="Loading AI model...")
def load_model():

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_NAME
    )

    model.eval()

    return tokenizer, model


# ==========================================
# 3. GENERATE AI RESPONSE
# ==========================================

def generate_response(
    question,
    profile,
    assistant_name,
    assistant_role,
    language,
    tone,
    instructions
):

    tokenizer, model = load_model()

    prompt = f"""
You are {assistant_name}, a helpful {assistant_role}.

USER PROFILE:
{profile[:1200]}

TASK:
Answer the following user question.

QUESTION:
{question[:500]}

REQUIREMENTS:
Write in {language}.
Use a {tone} tone.
{instructions[:300]}

Give a direct, useful and natural answer.
Do not repeat the question.
Do not repeat instructions.
Do not invent facts.
If information is unavailable, say so.

ANSWER:
"""

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512
    )

    with torch.no_grad():

        outputs = model.generate(
            **inputs,
            max_new_tokens=120,
            num_beams=4,
            repetition_penalty=1.8,
            no_repeat_ngram_size=3,
            early_stopping=True
        )

    answer = tokenizer.decode(
        outputs[0],
        skip_special_tokens=True
    ).strip()

    if not answer or len(answer.split()) < 4:

        return (
            "I couldn't generate a useful answer. "
            "Please try asking your question differently."
        )

    return answer


# ==========================================
# 4. SESSION STATE
# ==========================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "assistant_created" not in st.session_state:
    st.session_state.assistant_created = False


# ==========================================
# 5. HEADER
# ==========================================

st.title("🤖 FAHIM CUSTOM AI AGENT BUILDER")

st.markdown(
    """
    Create your personal AI assistant using your profile,
    business information and custom instructions.
    """
)

st.divider()


# ==========================================
# 6. SIDEBAR CONFIGURATION
# ==========================================

with st.sidebar:

    st.header("⚙️ Assistant Settings")

    assistant_name = st.text_input(
        "Assistant Name",
        value="My Personal AI"
    )

    assistant_role = st.text_input(
        "Assistant Role",
        value="Personal and Business Assistant"
    )

    language = st.selectbox(
        "Response Language",
        [
            "English",
            "Bengali",
            "Portuguese",
            "Hindi"
        ]
    )

    tone = st.selectbox(
        "Response Tone",
        [
            "Professional",
            "Friendly",
            "Simple",
            "Detailed"
        ]
    )

    st.divider()

    st.subheader("👤 Personal Master Profile")

    profile = st.text_area(
        "Your Personal Profile",
        height=250,
        placeholder=(
            "Paste your personal information, "
            "education, experience, skills, "
            "business details and portfolio links."
        )
    )

    st.divider()

    st.subheader("🧠 Custom Instructions")

    instructions = st.text_area(
        "Instructions for your AI",
        value=(
            "Give helpful and accurate answers. "
            "Use the supplied profile. "
            "Never invent personal facts, prices or links. "
            "If information is unavailable, say so. "
            "Keep answers relevant to the question."
        ),
        height=150
    )

    create_button = st.button(
        "🚀 Create My AI Assistant",
        use_container_width=True
    )

    if create_button:

        if not profile.strip():

            st.warning(
                "Please paste your personal profile first."
            )

        else:

            st.session_state.assistant_created = True
            st.session_state.messages = []

            st.success(
                "Your AI assistant is ready!"
            )

    if st.button(
        "🗑️ Clear Conversation",
        use_container_width=True
    ):

        st.session_state.messages = []

        st.rerun()


# ==========================================
# 7. MAIN CHAT INTERFACE
# ==========================================

st.subheader("💬 Chat With Your AI")

if not st.session_state.assistant_created:

    st.info(
        "Enter your personal profile in the sidebar "
        "and click Create My AI Assistant."
    )

else:

    st.success(
        f"Assistant active: {assistant_name}"
    )

    # Display previous messages

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])

    # Chat input

    user_question = st.chat_input(
        "Ask your AI assistant anything..."
    )

    if user_question:

        # Display user message

        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_question
            }
        )

        with st.chat_message("user"):

            st.markdown(user_question)

        # Generate assistant response

        with st.chat_message("assistant"):

            with st.spinner("AI is thinking..."):

                try:

                    answer = generate_response(
                        question=user_question,
                        profile=profile,
                        assistant_name=assistant_name,
                        assistant_role=assistant_role,
                        language=language,
                        tone=tone,
                        instructions=instructions
                    )

                    st.markdown(answer)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer
                        }
                    )

                except Exception as error:

                    st.error(
                        "Unable to generate a response."
                    )

                    st.code(str(error))


# ==========================================
# 8. EXPORT CONVERSATION
# ==========================================

st.divider()

st.subheader("📥 Export Your Conversation")

if st.session_state.messages:

    conversation_text = (
        "FAHIM CUSTOM AI AGENT BUILDER\n"
        f"Assistant: {assistant_name}\n"
        f"Exported: {datetime.now().isoformat()}\n"
        "====================================\n\n"
    )

    for message in st.session_state.messages:

        role = message["role"].upper()

        conversation_text += (
            f"{role}:\n"
            f"{message['content']}\n\n"
        )

    st.download_button(
        label="📄 Download TXT",
        data=conversation_text,
        file_name="fahim_ai_conversation.txt",
        mime="text/plain"
    )

    json_data = json.dumps(
        st.session_state.messages,
        ensure_ascii=False,
        indent=4
    )

    st.download_button(
        label="📦 Download JSON",
        data=json_data,
        file_name="fahim_ai_conversation.json",
        mime="application/json"
    )

else:

    # ==========================================
# 9. FOOTER
# ==========================================

st.divider()

st.markdown(
    """
    <div style="text-align:center; padding:15px;">
        <strong>FAHIM CUSTOM AI AGENT BUILDER PRO</strong><br>
        Personal AI Assistant | Powered by Hugging Face<br>
        🌐 Creative Design. Professional Results.
    </div>
    """,
    unsafe_allow_html=True
)
