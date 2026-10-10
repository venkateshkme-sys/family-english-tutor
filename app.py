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
st.set_page_config(page_title="Topic English Tutor", page_icon="🎙️")
st.title("🎙️ தலைப்பு வாரியான ஆங்கில ஆசிரியர் (Miss Nova)")

st.sidebar.header("🎯 உரையாடல் தலைப்புகள்")
topic = st.sidebar.selectbox(
    "உங்களுக்குப் பிடித்த தலைப்பைத் தேர்ந்தெடுக்கவும்:",
    ["Daily Life (தினசரி வாழ்க்கை)", "Job Interview (வேலை நேர்காணல்)", "At a Restaurant (உணவகம்)", "Shopping (அங்காடி)"]
)

initial_prompts = {
    "Daily Life (தினசரி வாழ்க்கை)": "Hello! Let's talk about daily life. How was your day today, and what did you do from morning?",
    "Job Interview (வேலை நேர்காணல்)": "Welcome to your mock interview. Can you please introduce yourself and tell me about your work experience?",
    "At a Restaurant (உணவகம்)": "Hello, welcome to our cafe! I am your waiter today. What would you like to order for dinner?",
    "Shopping (அங்காடி)": "Hi there! Welcome to our clothing store. Are you looking for anything specific today, like shirts or jeans?"
}

if "current_topic" not in st.session_state or st.session_state.current_topic != topic:
    st.session_state.current_topic = topic
    st.session_state.messages = [
        {"role": "system", "content": (
            f"You are Miss Nova, a friendly spoken English coach. The selected topic is '{topic}'. "
            "Your goal is to practice English conversation with the user related to this specific topic. "
            "Rule 1: Ask only ONE simple question at a time related to the scenario. "
            "Rule 2: Read the user's answer. If they make a grammar mistake, gently point it out as [Correction: ...], and then ask the NEXT logical question. "
            "Rule 3: Keep your responses short (1-3 sentences maximum)."
        )},
        {"role": "assistant", "content": initial_prompts[topic]}
    ]

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

# --- 3. AI ஆசிரியர் உரையாடலைத் தொடரும் செயல்பாடு (LLM) ---
def get_tutor_response():
    completion = groq_client.chat.completions.create(
        model="llama3-8b-8192", 
        messages=st.session_state.messages
    )
    return completion.choices.message.content

# --- 4. AI பதிலை குரலாக மாற்றும் செயல்பாடு (TTS) ---
async def text_to_speech(text_response, output_path):
    clean_text = text_response.replace("[Correction:", "Regarding your grammar, ")
    voice = "en-GB-SoniaNeural" 
    communicate = edge_tts.Communicate(clean_text, voice)
    await communicate.save(output_path)

# --- கடந்த கால உரையாடல்களைத் திரையில் காட்டுதல் ---
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

# --- வெப்சைட் இயங்கும் முறை ---
st.write("---")
audio_bytes = audio_recorder(text="பதிலளிக்க இங்கே க்ளிக் செய்து பேசவும்", recording_color="#e74c3c", neutral_color="#2ecc71")

if audio_bytes:
    with st.spinner("🤖 நீங்கள் பேசியதை AI புரிந்துகொள்கிறது..."):
        user_text = speech_to_text(audio_bytes)
        
    if user_text:
        st.session_state.messages.append({"role": "user", "content": user_text})
        
        with st.spinner("🧠 Miss Nova திருத்தங்கள் மற்றும் அடுத்த கேள்வியைத் தயாரிக்கிறார்..."):
            ai_reply = get_tutor_response()
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            
            output_audio_file = "reply.mp3"
            # 🚀 முக்கிய திருத்தம்: பழைய TypeError பிழை தரும் வரியை மாற்றி பாதுகாப்பாக இயக்கும் முறை
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(text_to_speech(ai_reply, output_audio_file))
            
        st.rerun()
    else:
        st.error("மன்னிக்கவும், உங்கள் குரல் சரியாகப் புரியவில்லை. மீண்டும் முயற்சிக்கவும்!")

# சமீபத்திய பதிலுக்கான ஆடியோ பிளேயரை மட்டும் கீழே காட்டுதல்
if os.path.exists("reply.mp3"):
    st.write("🔊 **Listen to Miss Nova's voice:**")
    st.audio("reply.mp3", format="audio/mp3")
