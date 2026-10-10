import streamlit as st
from audio_recorder_streamlit import audio_recorder
from groq import Groq
import edge_tts
import asyncio
import os

# --- 1. பாதுகாப்பான API Keys செட்டப் (Streamlit Secrets) ---
try:
    GROQ_API_KEY = st.secrets["YOUR_GROQ_KEY"]
except Exception:
    GROQ_API_KEY = "gsk_local_testing_only"

groq_client = Groq(api_key=GROQ_API_KEY)

# --- வெப்சைட் வடிவமைப்பு (UI Layout) ---
st.set_page_config(page_title="Family English Tutor", page_icon="🎙️")
st.title("🎙️ 10-நிமிட ஆங்கில உரையாடல் (Miss Nova)")

# --- வயது மற்றும் நபர் தேர்வு ---
st.sidebar.header("👤 யார் பேசுகிறார்கள்? (Who is speaking?)")
profile = st.sidebar.selectbox(
    "பயன்படுத்துபவரைத் தேர்ந்தெடுக்கவும்:",
    ["Child (குழந்தை - Age 5-12)", "Adult / Wife (பெரியவர்கள் / மனைவி)"]
)

st.sidebar.header("🎯 உரையாடல் தலைப்புகள்")
topic = st.sidebar.selectbox(
    "உங்களுக்குப் பிடித்த தலைப்பைத் தேர்ந்தெடுக்கவும்:",
    ["Daily Life (தினசரி வாழ்க்கை)", "Hobbies & Fun (பொழுதுபோக்கு)", "At a Restaurant (உணவகம்)", "Shopping (அங்காடி)"]
)

# வயதுக்கு தகுந்தவாறு தொடக்கக் கேள்விகள்
initial_prompts = {
    "Child (குழந்தை - Age 5-12)": {
        "Daily Life (தினசரி வாழ்க்கை)": "Hello little friend! How was your school today? What fun things did you do?",
        "Hobbies & Fun (பொழுதுபோக்கு)": "Hi! What is your favorite cartoon or game? Tell me why you love it!",
        "At a Restaurant (உணவகம்)": "Welcome to my ice cream parlor! What flavor do you want to eat today - chocolate or strawberry?",
        "Shopping (அங்காடி)": "Hello! Welcome to the toy store. What toy do you want to buy today?"
    },
    "Adult / Wife (பெரியவர்கள் / மனைவி)": {
        "Daily Life (தினசரி வாழ்க்கை)": "Hello! Let's talk about daily life. How was your day today, and what did you do from morning?",
        "Hobbies & Fun (பொழுதுபோக்கு)": "Hello! What do you like to do in your free time? Do you enjoy cooking, watching movies, or reading?",
        "At a Restaurant (உணவகம்)": "Hello, welcome to our cafe! I am your waiter today. What would you like to order for dinner?",
        "Shopping (அங்காடி)": "Hi there! Welcome to our clothing store. Are you looking for anything specific today, like shirts or dresses?"
    }
}

# நபர் அல்லது தலைப்பை மாற்றினால் உரையாடலையும் கவுண்ட்டரையும் ரீசெட் செய்ய
state_key = f"{profile}_{topic}"
if "current_state" not in st.session_state or st.session_state.current_state != state_key:
    st.session_state.current_state = state_key
    st.session_state.messages = [
        {"role": "assistant", "content": initial_prompts[profile][topic]}
    ]
    st.session_state.turn_count = 0  # 🚀 புதிய கவுண்ட்டர்: எத்தனை முறை பேசியுள்ளோம் என்பதைக் கணக்கிட

# திரையில் தற்போதைய முன்னேற்றத்தைக் காட்டுதல்
st.sidebar.write("---")
st.sidebar.subheader("⏱️ உரையாடல் முன்னேற்றம்")
# 15 டர்ன்கள் என்பது தோராயமாக 10 நிமிடப் பேச்சிற்குச் சமம்
progress = min(st.session_state.turn_count / 15, 1.0)
st.sidebar.progress(progress)
st.sidebar.write(f"பேசிய எண்ணிக்கை: {st.session_state.turn_count} / 15 வரம்புகள்")

# --- 2. Groq மூலம் பேச்சை ஆங்கில உரையாக மாற்றும் செயல்பாடு (STT) ---
def speech_to_text(audio_bytes):
    temp_filename = "temp_recording.wav"
    with open(temp_filename, "wb") as f:
        f.write(audio_bytes)
        
    try:
        with open(temp_filename, "rb") as audio_file:
            translation = groq_client.audio.translations.create(
                file=(temp_filename, audio_file.read()),
                model="whisper-large-v3",
                response_format="json"
            )
        transcribed_text = translation.text
    except Exception as e:
        st.error(f"STT Error: {e}")
        transcribed_text = None
        
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
        
    return transcribed_text

# --- 3. 10 நிமிட உரையாடலைத் தொடரும் AI ஆசிரியர் செயல்பாடு (LLM) ---
def get_tutor_response():
    # 10 நிமிட வரம்பு முடிந்துவிட்டால் உரையாடலை முடிக்கக் கட்டளையிடல்
    is_time_up = st.session_state.turn_count >= 15
    
    if profile == "Child (குழந்தை - Age 5-12)":
        ai_rules = (
            "You are Miss Nova, a sweet, loving, and encouraging English teacher for a child aged 5-12. Use very simple words. "
            "Behavior: "
            "1. Read the child's sentence. If they make a grammar mistake, show a very simple correction like [Correction: Say 'I went' instead of 'I go']. "
            "2. Praise them enthusiastically using words like 'Wow!', 'Super!'. "
        )
        if is_time_up:
            ai_rules += "3. Since the 10-minute session is finished, say a warm goodbye, praise their performance, and tell them to practice again tomorrow. Do NOT ask a new question."
        else:
            ai_rules += "3. Always end by asking ONE simple question related directly and relatively to their last answer to continue the chat."
            
    else:
        ai_rules = (
            f"You are Miss Nova, a supportive, polite English coach for an adult or housewife. The topic is '{topic}'. "
            "Behavior: "
            "1. If the user makes a grammar mistake, provide a gentle correction note labeled as [Correction: ...]. "
            "2. Respond conversationally to their answer in 1 sentence. "
        )
        if is_time_up:
            ai_rules += "3. Since the 10-minute session is complete, wrap up the conversation, give an overall encouragement, and say goodbye. Do NOT ask a new question."
        else:
            ai_rules += "3. Always end by asking a NEW interesting question that is relatively connected to their previous answer to keep the 10-minute interview going."

    system_instruction = {"role": "system", "content": ai_rules}
    payload = [system_instruction] + st.session_state.messages
    
    completion = groq_client.chat.completions.create(
        model="llama3-8b-8192", 
        messages=payload
    )
    return completion.choices.message.content

# --- 4. AI பதிலை குரலாக மாற்றும் செயல்பாடு (TTS) ---
async def text_to_speech(text_response, output_path):
    clean_text = text_response.replace("[Correction:", "Regarding your grammar, ")
    voice = "en-GB-SoniaNeural" 
    communicate = edge_tts.Communicate(clean_text, voice)
    await communicate.save(output_path)

# --- உரையாடல்களைத் திரையில் காட்டுதல் ---
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

# --- வெப்சைட் இயங்கும் முறை ---
st.write("---")

# 10 நிமிடம் முடிந்த பிறகு மைக் பட்டனை மறைத்து உரையாடலை முடிக்க
if st.session_state.turn_count >= 15:
    st.success("🎉 அருமை! உங்களது இன்றைய 10 நிமிட ஆங்கிலப் பயிற்சி வெற்றிகரமாக நிறைவடைந்தது!")
    if st.button("உரையாடலை மீண்டும் முதலிலிருந்து தொடங்க (Restart Chat)"):
        st.session_state.turn_count = 0
        st.session_state.messages = [{"role": "assistant", "content": initial_prompts[profile][topic]}]
        st.rerun()
else:
    audio_bytes = audio_recorder(text="பதிலளிக்க இங்கே க்ளிக் செய்து பேசவும்", recording_color="#e74c3c", neutral_color="#2ecc71")

    if audio_bytes:
        with st.spinner("🤖 நீங்கள் பேசியதை AI புரிந்துகொள்கிறது..."):
            user_text = speech_to_text(audio_bytes)
            
        if user_text:
            st.session_state.messages.append({"role": "user", "content": user_text})
            st.session_state.turn_count += 1  # கவுண்ட்டரை 1 கூட்டுகிறோம்
            
            with st.spinner("🧠 Miss Nova திருத்தங்கள் மற்றும் அடுத்த கேள்வியைத் தயாரிக்கிறார்..."):
                ai_reply = get_tutor_response()
                st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                
                output_audio_file = "reply.mp3"
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(text_to_speech(ai_reply, output_audio_file))
                
            st.rerun()
        else:
            st.error("மன்னிக்கவும், உங்கள் குரல் சரியாகப் புரியவில்லை. மீண்டும் முயற்சிக்கவும்!")

if os.path.exists("reply.mp3"):
    st.write("🔊 **Listen to Miss Nova's voice:**")
    st.audio("reply.mp3", format="audio/mp3")
