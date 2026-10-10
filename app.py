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

# Groq கிளையண்ட் - இது மட்டுமே இப்போது STT மற்றும் LLM இரண்டிற்கும் போதுமானது!
groq_client = Groq(api_key=GROQ_API_KEY)

# --- வெப்சைட் வடிவமைப்பு (UI Layout) ---
st.set_page_config(page_title="Family English Tutor", page_icon="🎙️")
st.title("🎙️ குடும்ப ஆங்கில ஆசிரியர் (Miss Nova)")
st.write("✨ **வழிமுறை:** கீழே உள்ள மைக் பட்டனை அழுத்தி தமிழில் அல்லது ஆங்கிலத்தில் பேசுங்கள். பேசி முடித்ததும் மீண்டும் அதே பட்டனை அழுத்தி நிறுத்தவும். AI உங்களுக்குப் பதிலளிக்கும்!")

# --- 2. Groq மூலம் பேச்சை மிக அதிவேகமாக உரையாக மாற்றும் செயல்பாடு (STT) ---
def speech_to_text(audio_bytes):
    temp_filename = "temp_recording.wav"
    with open(temp_filename, "wb") as f:
        f.write(audio_bytes)
        
    try:
        # 🚀 ஹக்கிங் ஃபேஸ்-க்கு பதிலாக Groq-இன் அதிவேக Whisper மாடலைப் பயன்படுத்துகிறோம்
        with open(temp_filename, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(temp_filename, audio_file.read()),
                model="whisper-large-v3", # உலகத்தரம் வாய்ந்த STT மாடல்
                response_format="json",
                language="ta" # தமிழ் மற்றும் ஆங்கிலக் கலவையைப் புரிந்துகொள்ளும்
            )
        transcribed_text = transcription.text
    except Exception as e:
        st.error(f"STT Error: {e}")
        transcribed_text = None
        
    # தற்காலிக ஃபைலை நீக்குதல்
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
        
    return transcribed_text

# --- 3. AI ஆசிரியர் பதில் தயாரிக்கும் செயல்பாடு (LLM) ---
def chat_with_tutor(user_text):
    system_prompt = (
        "You are Miss Nova, a friendly spoken English coach for a family. "
        "Keep your response strictly to 1 or 2 simple sentences. "
        "If the user made any grammar mistakes, gently add a correction note at the end labeled as [Correction: ...]."
    )
    completion = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]
    )
    return completion.choices.message.content

# --- 4. AI பதிலை குரலாக மாற்றும் செயல்பாடு (TTS) ---
async def text_to_speech(text_response, output_path):
    clean_text = text_response.replace("[Correction:", "Regarding your grammar, ")
    voice = "en-GB-SoniaNeural" 
    communicate = edge_tts.Communicate(clean_text, voice)
    await communicate.save(output_path)

# --- வெப்சைட் இயங்கும் முறை ---
audio_bytes = audio_recorder(text="பேச இங்கே க்ளிக் செய்யவும்", recording_color="#e74c3c", neutral_color="#2ecc71")

if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
    
    with st.spinner("🤖 நீங்கள் பேசியதை AI புரிந்துகொள்கிறது..."):
        transcribed_text = speech_to_text(audio_bytes)
        
    if transcribed_text:
        st.success(f"🗣️ நீங்கள் பேசியது: {transcribed_text}")
        
        with st.spinner("🧠 AI ஆசிரியர் பதில் தயாரிக்கும் செயல்பாடு..."):
            ai_reply = chat_with_tutor(transcribed_text)
            output_audio_file = "reply.mp3"
            asyncio.run(text_to_speech(ai_reply, output_audio_file))
        
        st.markdown(f"### 🤖 Miss Nova-வின் பதில்:")
        st.info(ai_reply)
        st.audio(output_audio_file, format="audio/mp3")
    else:
        st.error("மன்னிக்கவும், உங்கள் குரல் சரியாகப் புரியவில்லை. மீண்டும் முயற்சிக்கவும்!")
