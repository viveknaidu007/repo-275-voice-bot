import streamlit as st
import speech_recognition as sr
import google.generativeai as genai
from dotenv import load_dotenv
import os
import io
import time
import threading
from typing import Optional

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

AUDIO_RECORDER_AVAILABLE = False  # Disabled for compatibility

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="Voice Bot Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        font-size: 2.5rem;
        margin-bottom: 2rem;
    }
    .chat-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .user-message {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #2196f3;
    }
    .bot-message {
        background-color: #f1f8e9;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #4caf50;
    }
    .voice-button {
        background-color: #ff4444;
        color: white;
        border: none;
        border-radius: 50px;
        padding: 1rem 2rem;
        font-size: 1.2rem;
        cursor: pointer;
    }
    .status-indicator {
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        text-align: center;
        font-weight: bold;
    }
    .status-listening {
        background-color: #ffebee;
        color: #c62828;
    }
    .status-processing {
        background-color: #fff3e0;
        color: #ef6c00;
    }
    .status-ready {
        background-color: #e8f5e8;
        color: #2e7d32;
    }
</style>
""", unsafe_allow_html=True)

class VoiceBot:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.setup_microphone()
        self.setup_tts()
        self.setup_gemini()
    
    def setup_microphone(self):
        """Setup microphone with fallback options"""
        try:
            self.microphone = sr.Microphone()
            self.microphone_available = True
        except Exception as e:
            st.warning(f"⚠️ Microphone setup issue: {e}")
            st.info("💡 You can still use text input or file upload for voice.")
            self.microphone_available = False
        
    def setup_tts(self):
        """Configure text-to-speech engine"""
        if not PYTTSX3_AVAILABLE:
            st.info("ℹ️ Text-to-speech not available in cloud deployment. Responses will be text-only.")
            self.tts_available = False
            return
            
        try:
            self.tts_engine = pyttsx3.init()
            voices = self.tts_engine.getProperty('voices')
            if voices:
                # Try to use a female voice if available
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
                else:
                    self.tts_engine.setProperty('voice', voices[0].id)
            
            self.tts_engine.setProperty('rate', 180)  # Speed of speech
            self.tts_engine.setProperty('volume', 0.8)  # Volume level
            self.tts_available = True
        except Exception as e:
            st.warning(f"⚠️ Text-to-speech not available: {e}")
            self.tts_available = False
    
    def setup_gemini(self):
        """Configure Gemini API"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key or api_key == 'your_gemini_api_key_here':
            st.error("❌ Please set your GEMINI_API_KEY in the .env file")
            st.stop()
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def listen_for_speech(self, timeout: int = 5) -> Optional[str]:
        """Capture and convert speech to text"""
        if not self.microphone_available:
            st.error("❌ Microphone not available. Please use text input or upload an audio file.")
            return None
            
        try:
            with self.microphone as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                st.info("🎤 Listening... Please speak now!")
                
                # Listen for audio with timeout
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                
                st.info("🔄 Processing speech...")
                # Convert speech to text
                text = self.recognizer.recognize_google(audio)
                return text
                
        except sr.WaitTimeoutError:
            st.warning("⏰ No speech detected. Please try again.")
            return None
        except sr.UnknownValueError:
            st.warning("❓ Could not understand the speech. Please try again.")
            return None
        except sr.RequestError as e:
            st.error(f"❌ Speech recognition error: {e}")
            return None
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")
            return None
    
    def process_audio_file(self, audio_bytes) -> Optional[str]:
        """Process uploaded audio file"""
        try:
            # Save audio bytes to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name
            
            # Use speech recognition on the file
            with sr.AudioFile(tmp_file_path) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio)
                
            # Clean up
            os.unlink(tmp_file_path)
            return text
            
        except Exception as e:
            st.error(f"❌ Error processing audio file: {e}")
            return None
    
    def get_personal_context(self) -> str:
        """Return personal context for the AI to respond as the applicant"""
        return """
        Answer the questions naturally and conversationally,
        Keep responses concise but informative.
        """
    
    def generate_response(self, question: str) -> str:
        """Generate response using Gemini API"""
        try:
            context = self.get_personal_context()
            prompt = f"{context}\n\n Question: {question}\n\nYour Response:"
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            return f"I apologize, I'm having trouble processing that question right now. Error: {str(e)}"
    
    def speak_text(self, text: str):
        """Convert text to speech"""
        if not self.tts_available:
            st.info("🔊 Text-to-speech not available. Response shown as text.")
            return
            
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            st.error(f"Text-to-speech error: {e}")

def main():
    # Header
    st.markdown('<h1 class="main-header">🤖 Voice Bot </h1>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'voice_bot' not in st.session_state:
        st.session_state.voice_bot = VoiceBot()
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'is_listening' not in st.session_state:
        st.session_state.is_listening = False
    
    # Sidebar
    with st.sidebar:
        st.header("🎯 Interview Voice Bot")
        st.markdown("""
        This voice bot is designed to answer interview questions as the job applicant.
        
        **How to use:**
        1. Click 'Start Voice Input' to speak your question
        2. Or type your question in the text box
        3. Get personalized responses
        
        **Sample Questions:**
        - What should we know about your life story?
        - What's your #1 superpower?
        - What are the top 3 areas you'd like to grow in?
        - What misconception do your coworkers have about you?
        - How do you push your boundaries and limits?
        """)
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("💬 Chat Interface")
        
        # Voice input section
        st.markdown("### 🎤 Voice Input")
        
        # Multiple voice input options
        voice_tab1, voice_tab2 = st.tabs(["🎙️ Live Recording", "📁 Upload Audio"])
        
        with voice_tab1:
            if st.session_state.voice_bot.microphone_available:
                if st.button("🎤 Start Voice Input", key="voice_button", help="Click and speak your question"):
                    with st.spinner("Listening for your question..."):
                        question = st.session_state.voice_bot.listen_for_speech(timeout=10)
                        
                        if question:
                            st.success(f"📝 Captured: {question}")
                            
                            # Add to chat history
                            st.session_state.chat_history.append({"role": "user", "content": question})
                            
                            # Generate response
                            with st.spinner("🤔 Generating response..."):
                                response = st.session_state.voice_bot.generate_response(question)
                                st.session_state.chat_history.append({"role": "assistant", "content": response})
                            
                            # Speak the response
                            if st.session_state.voice_bot.tts_available:
                                with st.spinner("🔊 Speaking response..."):
                                    st.session_state.voice_bot.speak_text(response)
                            
                            st.rerun()
            else:
                st.warning("🎙️ Direct microphone access not available. Use other voice input methods below.")
        
        with voice_tab2:
            uploaded_audio = st.file_uploader(
                "Upload an audio file (WAV, MP3, M4A)", 
                type=['wav', 'mp3', 'm4a'],
                help="Record a question on your phone and upload it here"
            )
            
            if uploaded_audio is not None:
                st.audio(uploaded_audio, format='audio/wav')
                
                if st.button("🔄 Process Audio File", key="process_audio"):
                    with st.spinner("Processing uploaded audio..."):
                        audio_bytes = uploaded_audio.read()
                        question = st.session_state.voice_bot.process_audio_file(audio_bytes)
                        
                        if question:
                            st.success(f"📝 Captured from file: {question}")
                            
                            # Add to chat history
                            st.session_state.chat_history.append({"role": "user", "content": question})
                            
                            # Generate response
                            with st.spinner("🤔 Generating response..."):
                                response = st.session_state.voice_bot.generate_response(question)
                                st.session_state.chat_history.append({"role": "assistant", "content": response})
                            
                            st.rerun()
        
        with voice_tab3:
            if AUDIO_RECORDER_AVAILABLE:
                st.info("� Click to start/stop recording")
                # audio_bytes = audio_recorder(text="Click to record", recording_color="#e74c3c", neutral_color="#34495e")
                audio_bytes = None  # Disabled for compatibility
                
                if False:  # audio_bytes:
                    st.audio(audio_bytes, format="audio/wav")
                    
                    if st.button("🔄 Process Recording", key="process_recording"):
                        with st.spinner("Processing recording..."):
                            question = st.session_state.voice_bot.process_audio_file(audio_bytes)
                            
                            if question:
                                st.success(f"📝 Captured from recording: {question}")
                                
                                # Add to chat history
                                st.session_state.chat_history.append({"role": "user", "content": question})
                                
                                # Generate response
                                with st.spinner("🤔 Generating response..."):
                                    response = st.session_state.voice_bot.generate_response(question)
                                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                                
                                st.rerun()
            else:
                st.info("📦 Web recorder not available. Install streamlit-audio-recorder for this feature.")
        
        # Text input section
        st.markdown("### ⌨️ Text Input")
        text_question = st.text_area(
            "Type your interview question:",
            placeholder="e.g., What should we know about your life story in a few sentences?",
            height=100
        )
        
        if st.button("📤 Send Question", key="text_button"):
            if text_question.strip():
                # Add to chat history
                st.session_state.chat_history.append({"role": "user", "content": text_question})
                
                # Generate response
                with st.spinner("🤔 Generating response..."):
                    response = st.session_state.voice_bot.generate_response(text_question)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                
                st.rerun()
        
        # Chat history display
        st.markdown("### 💭 Conversation History")
        if st.session_state.chat_history:
            for i, message in enumerate(st.session_state.chat_history):
                if message["role"] == "user":
                    st.markdown(f'<div class="user-message"><strong>🧑 Interviewer:</strong> {message["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="bot-message"><strong>🤖 Candidate:</strong> {message["content"]}</div>', unsafe_allow_html=True)
        else:
            st.info("👋 Start the conversation by asking an interview question!")
    
    with col2:
        st.subheader("📋 Instructions")
        st.markdown("""
        **Quick Start:**
        1. Make sure your microphone is working
        2. Click the voice button to ask questions
        3. Or type your questions manually
        4. The bot will respond
        
        **Technical Notes:**
        - Uses Google Speech Recognition
        - Powered by Gemini AI
        - Text-to-speech for audio responses
        - Designed for 100x AI Agent Team interview
        """)
        
        # Status indicator
        if st.session_state.is_listening:
            st.markdown('<div class="status-indicator status-listening">🎤 LISTENING</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-indicator status-ready">✅ READY</div>', unsafe_allow_html=True)
        
        # Sample questions
        st.markdown("**💡 Sample Questions:**")
        sample_questions = [
            "What should we know about your life story?",
            "What's your #1 superpower?",
            "What are the top 3 areas you'd like to grow in?",
            "What misconception do your coworkers have about you?",
            "How do you push your boundaries and limits?"
        ]
        
        for question in sample_questions:
            if st.button(f"❓ {question}", key=f"sample_{question}"):
                # Add to chat history
                st.session_state.chat_history.append({"role": "user", "content": question})
                
                # Generate response
                with st.spinner("🤔 Generating response..."):
                    response = st.session_state.voice_bot.generate_response(question)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                
                st.rerun()

if __name__ == "__main__":
    main()