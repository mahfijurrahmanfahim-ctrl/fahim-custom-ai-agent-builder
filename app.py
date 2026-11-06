import streamlit as st
from datetime import datetime

# ==========================================
# 1. APP CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="FAHIM CUSTOM AI AGENT BUILDER PRO",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_NAME = "FAHIM CUSTOM AI AGENT BUILDER PRO"

# ==========================================
# 2. SESSION STATE
# ==========================================

defaults = {
    "messages": [],
    "assistant_name": "Fahim AI",
    "assistant_role": "Personal AI Assistant",
    "profile": """
Name: Mahfijur Rahman Fahim
Business: Fahim Graphic Design

Skills:
- Graphic Design
- AI-assisted Image Editing
- Restaurant Menu Design
- Social Media Design
- Posters and Banners
- Business Advertising
- Video Production

Portfolio:
https://mahfijurrahmanfahim-ctrl.github.io/fahim-graphic-design-portfolio/

Fiverr:
https://www.fiverr.com/s/X00EVme
https://www.fiverr.com/s/qbbQr6y
""",
    "instructions": (
        "Be helpful, accurate, friendly and professional. "
        "Never invent facts. Clearly explain limitations."
    ),
    "language": "Auto Detect",
    "style": "Professional",
    "demo_count": 0
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================
# 3. OFFLINE RESPONSE ENGINE
# ==========================================

def offline_response(prompt):

    original = prompt.strip()
    text = original.lower()

    profile = st.session_state.profile
    name = st.session_state.assistant_name
    role = st.session_state.assistant_role
    instructions = st.session_state.instructions

    # Empty input
    if not original:
        return "Please enter a message."

    # Greeting
    greetings = [
        "hello", "hi", "hey", "হ্যালো",
        "হাই", "আসসালামু", "good morning",
        "good evening"
    ]

    if any(word in text for word in greetings):

        return (
            f"Hello! 👋\n\n"
            f"I am {name}, your {role}.\n\n"
            "আমি Offline Demo Mode-এ কাজ করছি। "
            "আপনি আমার বিভিন্ন ফিচার পরীক্ষা করতে পারেন।"
        )

    # Help
    if any(word in text for word in [
        "help", "সাহায্য", "কি করতে পারো",
        "what can you do", "features"
    ]):

        return """
### 🤖 Available Demo Features

1. Greeting and basic conversation
2. User profile display
3. Business information
4. Graphic design suggestions
5. Restaurant menu guidance
6. Social media content templates
7. Basic programming guidance
8. Conversation history
9. Custom instructions
10. Chat export

**Note:** These are predefined offline responses,
not real AI-generated answers.
"""

    # Identity
    if any(word in text for word in [
        "who are you", "তুমি কে", "তোমার নাম",
        "your name", "তোমার পরিচয়"
    ]):

        return (
            f"My name is {name}.\n\n"
            f"My role is {role}.\n\n"
            "I am currently running in Offline Demo Mode."
        )

    # User profile
    if any(word in text for word in [
        "my profile", "আমার প্রোফাইল",
        "আমার পরিচয়", "about me",
        "who am i", "আমার সম্পর্কে"
    ]):

        return (
            "### 👤 User Profile\n\n"
            + profile
        )

    # Business
    if any(word in text for word in [
        "business", "ব্যবসা",
        "fahim graphic", "graphic design"
    ]):

        return """
### 🎨 Fahim Graphic Design

Available services:

- Professional graphic design
- Restaurant menu design
- Social media posts
- Promotional posters
- Business advertisements
- AI-assisted image editing
- Video promotional content

Portfolio:
https://mahfijurrahmanfahim-ctrl.github.io/fahim-graphic-design-portfolio/

**This information comes from your saved demo profile.**
"""

    # Restaurant menu
    if any(word in text for word in [
        "menu", "restaurant", "রেস্টুরেন্ট",
        "food design", "মেনু"
    ]):

        return """
### 🍽️ Restaurant Menu Design

A professional restaurant menu should include:

1. Restaurant name and branding
2. Clear food categories
3. Accurate item names
4. Correct prices
5. High-quality food photography
6. Readable typography
7. Consistent colour palette
8. Contact information

Never use invented menu prices or food items.
"""

    # Social media
    if any(word in text for word in [
        "social media", "facebook post",
        "instagram", "সোশ্যাল মিডিয়া"
    ]):

        return """
### 📱 Social Media Design

A good promotional post needs:

- Strong visual headline
- High-quality image
- Clear brand identity
- Readable typography
- Relevant call to action
- Correct contact information

Recommended formats:
- Instagram portrait: 1080 × 1350
- Instagram square: 1080 × 1080
- Story: 1080 × 1920
"""

    # Programming
    if any(word in text for word in [
        "python", "programming", "code",
        "coding", "streamlit", "app.py"
    ]):

        return """
### 💻 Programming Demo

This application is built with Python and Streamlit.

You can test:
- Chat interface
- Session state
- User inputs
- Conditional responses
- Conversation history
- Download functionality

This offline version cannot execute arbitrary
programming requests like a real coding AI.
"""

    # Instructions
    if any(word in text for word in [
        "instruction", "system prompt",
        "সিস্টেম নির্দেশনা"
    ]):

        return (
            "### ⚙️ Current Assistant Instructions\n\n"
            + instructions
        )

    # Time
    if any(word in text for word in [
        "date", "time", "তারিখ", "সময়"
    ]):

        return (
            "Current application date and time:\n\n"
            + datetime.now().strftime("%d %B %Y, %I:%M %p")
        )

    # Default fallback
    return f"""
### 📝 Offline Demo Response

**Your message:**

{original}

**Status:** Message received successfully.

আমি আপনার মেসেজ গ্রহণ করেছি। কিন্তু বর্তমানে
আমার কোনো AI language model সংযুক্ত নেই।

এটি একটি Offline Demo Response।

আপনি Chat Interface, Profile, Settings এবং
Conversation History পরীক্ষা করতে পারেন।

**Assistant:** {name}
"""


# ==========================================
# 4. SIDEBAR
# ==========================================

with st.sidebar:

    st.title("🤖 FAHIM AI")

    st.caption("Custom AI Agent Builder Pro")

    st.success("OFFLINE MODE ACTIVE")

    st.caption("No API • No Billing • No API Calls")

    st.divider()

    st.subheader("⚙️ Assistant Settings")

    st.session_state.assistant_name = st.text_input(
        "Assistant Name",
        value=st.session_state.assistant_name
    )

    st.session_state.assistant_role = st.text_input(
        "Assistant Role",
        value=st.session_state.assistant_role
    )

    st.session_state.language = st.selectbox(
        "Response Language",
        [
            "Auto Detect",
            "English",
            "Bangla",
            "Bangla + English"
        ],
        index=[
            "Auto Detect",
            "English",
            "Bangla",
            "Bangla + English"
        ].index(st.session_state.language)
    )

    st.session_state.style = st.selectbox(
        "Communication Style",
        [
            "Professional",
            "Friendly",
            "Simple",
            "Detailed",
            "Technical",
            "Creative"
        ],
        index=[
            "Professional",
            "Friendly",
            "Simple",
            "Detailed",
            "Technical",
            "Creative"
        ].index(st.session_state.style)
    )

    st.divider()

    with st.expander("👤 Personal Profile"):

        st.session_state.profile = st.text_area(
            "Your Profile",
            value=st.session_state.profile,
            height=250
        )

    with st.expander("🧠 System Instructions"):

        st.session_state.instructions = st.text_area(
            "Custom Instructions",
            value=st.session_state.instructions,
            height=180
        )

    st.divider()

    st.subheader("📊 Usage Statistics")

    st.metric(
        "Messages",
        len(st.session_state.messages)
    )

    st.metric(
        "Demo Responses",
        st.session_state.demo_count
    )

    st.caption("Offline demo usage. No API usage.")

    st.divider()

    if st.button(
        "🗑️ Clear All Chats",
        use_container_width=True
    ):

        st.session_state.messages = []
        st.session_state.demo_count = 0
        st.rerun()

    if st.button(
        "↩️ Reset Settings",
        use_container_width=True
    ):

        for key, value in defaults.items():
            st.session_state[key] = value

        st.rerun()


# ==========================================
# 5. MAIN HEADER
# ==========================================

st.title("🤖 FAHIM CUSTOM AI AGENT BUILDER PRO")

st.caption(
    "Personal AI Assistant | Offline Testing Edition"
)

col1, col2, col3 = st.columns(3)

with col1:
    st.info("🔌 API: Not Required")

with col2:
    st.success("🟢 Offline: Active")

with col3:
    st.info("💰 API Cost: Zero")


st.divider()


# ==========================================
# 6. CHAT DISPLAY
# ==========================================

st.subheader("💬 AI Conversation")

if not st.session_state.messages:

    st.markdown(
        f"### Welcome to {st.session_state.assistant_name}!"
    )

    st.write(
        "আপনার Offline Assistant পরীক্ষা শুরু করুন।"
    )

    suggestions = [
        "Hello",
        "Who are you?",
        "Show my profile",
        "What can you do?",
        "Tell me about my business"
    ]

    cols = st.columns(len(suggestions))

    for i, suggestion in enumerate(suggestions):

        with cols[i]:

            if st.button(
                suggestion,
                use_container_width=True
            ):

                st.session_state.pending_prompt = suggestion
                st.rerun()


# Display existing conversation

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ==========================================
# 7. USER INPUT
# ==========================================

prompt = st.chat_input(
    "আপনার প্রশ্ন লিখুন... / Ask anything..."
)

if "pending_prompt" in st.session_state:

    prompt = st.session_state.pop("pending_prompt")


# ==========================================
# 8. PROCESS MESSAGE
# ==========================================

if prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):

        st.markdown(prompt)

    with st.chat_message("assistant"):

        response = offline_response(prompt)

        st.markdown(response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })

    st.session_state.demo_count += 1


# ==========================================
# 9. EXPORT CONVERSATION
# ==========================================

st.divider()

st.subheader("💾 Conversation Management")

if st.session_state.messages:

    conversation = ""

    for message in st.session_state.messages:

        role = message["role"].upper()

        conversation += (
            f"\n{role}:\n"
            f"{message['content']}\n"
        )

    st.download_button(
        label="📥 Download Chat History",
        data=conversation,
        file_name="fahim_ai_chat_history.txt",
        mime="text/plain",
        use_container_width=True
    )

else:

    st.caption("No conversations to export yet.")


# ==========================================
# 10. FOOTER
# ==========================================

st.divider()

st.markdown(
    """
    <div style="text-align:center; padding:15px;">
        <h4>FAHIM CUSTOM AI AGENT BUILDER PRO</h4>
        <p>Creative Design. Professional Results.</p>
        <p>Offline Testing Edition</p>
        <small>
        Built for Fahim Graphic Design
        </small>
    </div>
    """,
    unsafe_allow_html=True
)
