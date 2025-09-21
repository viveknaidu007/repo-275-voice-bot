import streamlit as st
import speech_recognition as sr
import google.generativeai as genai
from dotenv import load_dotenv
import os
import io
import time
import threading
from typing import Optional
import tempfile
import wave

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

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
        color: #2e7d32;
        font-weight: 500;
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
            if SOUNDDEVICE_AVAILABLE:
                # Test sounddevice
                sd.query_devices()
                self.microphone_available = True
                self.microphone_method = "sounddevice"
            else:
                # Fallback to speech_recognition microphone
                self.microphone = sr.Microphone()
                self.microphone_available = True
                self.microphone_method = "speech_recognition"
        except Exception as e:
            st.warning(f"⚠️ Microphone setup issue: {e}")
            st.info("💡 You can still use text input or file upload for voice.")
            self.microphone_available = False
            self.microphone_method = None
        
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
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def listen_for_speech(self, timeout: int = 5) -> Optional[str]:
        """Capture and convert speech to text"""
        if not self.microphone_available:
            st.error("❌ Microphone not available. Please use text input or upload an audio file.")
            return None
        
        if self.microphone_method == "sounddevice":
            return self.listen_with_sounddevice(timeout)
        else:
            return self.listen_with_speech_recognition(timeout)
    
    def listen_with_sounddevice(self, duration: int = None) -> Optional[str]:
        """Record audio using sounddevice with start/stop control"""
        try:
            samplerate = 16000  # 16kHz sample rate
            max_duration = 30  # Maximum 30 seconds to prevent memory issues
            
            if duration:
                # Fixed duration recording (fallback)
                st.info("🎤 Recording... Speak now!")
                audio_data = sd.rec(int(samplerate * duration), samplerate=samplerate, 
                                  channels=1, dtype='int16')
                sd.wait()
            else:
                # Manual start/stop recording
                if 'recording' not in st.session_state:
                    st.session_state.recording = False
                if 'recorded_audio' not in st.session_state:
                    st.session_state.recorded_audio = None
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    if not st.session_state.recording:
                        if st.button("🎤 Start Recording", key="start_recording", type="primary"):
                            st.session_state.recording = True
                            st.session_state.recorded_audio = []
                            st.rerun()
                    else:
                        if st.button("⏹️ Stop Recording", key="stop_recording", type="secondary"):
                            st.session_state.recording = False
                            st.rerun()
                
                with col2:
                    if st.session_state.recording:
                        st.error("🔴 Recording... Click Stop when finished")
                    else:
                        st.success("⚪ Ready to record")
                
                # Handle recording state
                if st.session_state.recording:
                    # Start recording in a thread-safe way
                    if 'recording_started' not in st.session_state:
                        st.session_state.recording_started = True
                        # Use a shorter chunk to allow for responsive stop
                        chunk_duration = 1  # 1 second chunks
                        audio_data = sd.rec(int(samplerate * chunk_duration), samplerate=samplerate, 
                                          channels=1, dtype='int16')
                        sd.wait()
                        if st.session_state.recorded_audio is None:
                            st.session_state.recorded_audio = audio_data
                        else:
                            st.session_state.recorded_audio = np.concatenate([st.session_state.recorded_audio, audio_data])
                    return None  # Still recording
                
                elif st.session_state.recorded_audio is not None:
                    # Recording stopped, process the audio
                    audio_data = st.session_state.recorded_audio
                    st.session_state.recorded_audio = None
                    st.session_state.recording_started = False
                else:
                    return None  # No recording to process
            
            if 'audio_data' not in locals():
                return None
                
            st.info("🔄 Processing speech...")
            
            # Save to temporary wav file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                # Convert to wav format
                with wave.open(tmp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(samplerate)
                    wav_file.writeframes(audio_data.tobytes())
                
                # Use speech recognition on the file
                with sr.AudioFile(tmp_file.name) as source:
                    audio = self.recognizer.record(source)
                    text = self.recognizer.recognize_google(audio)
                
                # Clean up
                os.unlink(tmp_file.name)
                return text
                
        except Exception as e:
            st.error(f"❌ Recording error: {e}")
            return None
    
    def listen_with_speech_recognition(self, timeout: int = 5) -> Optional[str]:
        """Original speech recognition method"""
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
        You are responding as a job applicant for a position at 100x, an AI Agent Team. 
        Please respond in first person as if you are the candidate being interviewed.
        
        Background context about the candidate:
        - Experienced software developer with expertise in AI/ML and full-stack development
        - Passionate about building AI agents and automation tools
        - Strong background in Python, JavaScript, and modern frameworks
        - Has worked on various AI projects including chatbots, recommendation systems, and data analysis
        - Values continuous learning and staying updated with latest AI technologies
        - Enjoys problem-solving and building solutions that make a real impact
        - Good team player with excellent communication skills
        - Remote work experience and self-motivated
        
        Answer the interview question naturally and conversationally, as if you're speaking directly to the interviewer.
        Keep responses concise but informative (2-3 sentences typically).
        Be specific and give concrete examples when possible.
        """
    
    def generate_response(self, question: str) -> str:
        """Generate response using Gemini API"""
        try:
            context = self.get_personal_context()
            prompt = f"{context}\n\nInterview Question: {question}\n\nYour Response:"
            
            # Try the new model first
            try:
                response = self.model.generate_content(prompt)
                if response.text:
                    return response.text.strip()
                else:
                    return "I'm processing your question. Could you please rephrase it or ask another interview question?"
            except Exception as model_error:
                # Fallback to alternative model if available
                st.warning(f"⚠️ Primary model unavailable: {model_error}")
                try:
                    # Try with gemini-1.5-pro as fallback
                    fallback_model = genai.GenerativeModel('gemini-1.5-pro')
                    response = fallback_model.generate_content(prompt)
                    if response.text:
                        return response.text.strip()
                except:
                    pass
                
                # If all models fail, provide a helpful response
                return self.get_fallback_response(question)
            
        except Exception as e:
            st.error(f"❌ API Error: {str(e)}")
            return self.get_fallback_response(question)
    
    def get_fallback_response(self, question: str) -> str:
        """Provide fallback responses when API is unavailable"""
        fallback_responses = {
            "life story": "I'm a passionate software developer with over 5 years of experience in AI/ML and full-stack development. I've worked on various projects from chatbots to recommendation systems, and I'm always excited about learning new technologies. I believe in building solutions that make a real impact, and I'm particularly interested in AI agents and automation tools.",
            "superpower": "My #1 superpower is probably my ability to break down complex problems into manageable pieces. I can take a challenging technical requirement and systematically work through it, finding creative solutions along the way. I also have a knack for explaining technical concepts in simple terms.",
            "grow": "The top 3 areas I'd like to grow in are: 1) Advanced AI model architecture and optimization, 2) Leadership and team management skills, and 3) Understanding business strategy to better align technical solutions with company goals.",
            "misconception": "Some coworkers think I'm too focused on perfection, but actually I believe in iterative improvement. I like to get a working solution quickly and then refine it based on feedback rather than trying to make everything perfect from the start.",
            "boundaries": "I push my boundaries by taking on projects outside my comfort zone and actively seeking feedback. I also participate in hackathons, contribute to open source projects, and constantly learn new technologies through online courses and technical blogs."
        }
        
        question_lower = question.lower()
        for key, response in fallback_responses.items():
            if key in question_lower:
                return response
        
        return "Thank you for that question. I'd be happy to discuss my experience in AI/ML development, my passion for building innovative solutions, and how I can contribute to the 100x team. Could you perhaps rephrase the question or ask about a specific aspect of my background?"
    
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
    st.set_page_config(
        page_title="🎯 100x Voice Interview Bot",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Custom CSS for ChatGPT-style interface
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 15px;
        border-left: 4px solid;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .user-message {
        background-color: #f0f2f6;
        border-left-color: #1f77b4;
    }
    .bot-message {
        background-color: #e8f5e8;
        border-left-color: #28a745;
    }
    .input-container {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .recording-indicator {
        background: linear-gradient(45deg, #ff6b6b, #ee5a6f);
        color: white;
        padding: 12px;
        border-radius: 10px;
        text-align: center;
        margin: 15px 0;
        animation: pulse 2s infinite;
        box-shadow: 0 4px 8px rgba(255,107,107,0.3);
    }
    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.02); opacity: 0.8; }
        100% { transform: scale(1); opacity: 1; }
    }
    .status-ready {
        background-color: #28a745;
        color: white;
        padding: 8px;
        border-radius: 8px;
        text-align: center;
        margin: 5px 0;
    }
    .welcome-message {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        border: 2px dashed #ffc107;
        margin: 20px 0;
    }
    .stButton > button {
        border-radius: 10px;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'voice_bot' not in st.session_state:
        st.session_state.voice_bot = VoiceBot()
    
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    
    if 'main_text_input' not in st.session_state:
        st.session_state.main_text_input = ""
    
    # Main header
    st.markdown("""
    <div class="main-header">
        <h1>🎯 100x AI Agent Team Interview</h1>
        <p>Practice interview questions with ChatGPT-style voice and text input</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create layout - ChatGPT style
    chat_col, sidebar_col = st.columns([3, 1])
    
    with chat_col:
        # Chat history display (top section)
        st.markdown("## 💬 Interview Conversation")
        
        # Chat messages container with better styling
        chat_container = st.container()
        
        with chat_container:
            if st.session_state.chat_history:
                for i, message in enumerate(st.session_state.chat_history):
                    if message["role"] == "user":
                        st.markdown(f'''
                        <div class="chat-message user-message">
                            <strong>🧑 Interviewer:</strong><br>
                            <span style="font-size: 16px; color: #333; line-height: 1.5;">{message["content"]}</span>
                        </div>
                        ''', unsafe_allow_html=True)
                    else:
                        st.markdown(f'''
                        <div class="chat-message bot-message">
                            <strong>🤖 Candidate (You):</strong><br>
                            <span style="font-size: 16px; color: #333; line-height: 1.5;">{message["content"]}</span>
                        </div>
                        ''', unsafe_allow_html=True)
            else:
                st.markdown('''
                <div class="welcome-message">
                    <h3>👋 Welcome to your 100x Interview Practice!</h3>
                    <p style="color: #856404; margin: 10px 0;">Ask interview questions using voice or text below and get AI-powered responses.</p>
                    <p style="color: #6c757d; font-size: 14px;">✨ This bot will respond as the job candidate for the 100x AI Agent Team position.</p>
                </div>
                ''', unsafe_allow_html=True)
        
        # Input section - ChatGPT style (bottom section)
        st.markdown("---")
        
        # Input container with better styling
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        
        # ChatGPT-style input row
        text_col, voice_col, send_col = st.columns([6, 1.5, 1])
        
        with text_col:
            # Text area similar to ChatGPT
            text_question = st.text_area(
                "",
                placeholder="Ask your interview question here... (e.g., What should we know about your life story?)",
                height=80,
                key="main_text_input",
                label_visibility="collapsed"
            )
        
        with voice_col:
            st.markdown("<br>", unsafe_allow_html=True)
            # Voice recording toggle button
            if not st.session_state.is_recording:
                if st.button("🎤 Start", key="start_rec", use_container_width=True, help="Start voice recording"):
                    st.session_state.is_recording = True
                    st.rerun()
            else:
                if st.button("⏹️ Stop", key="stop_rec", use_container_width=True, help="Stop recording and process"):
                    st.session_state.is_recording = False
                    
                    # Process voice recording
                    with st.spinner("🎤 Processing your voice..."):
                        question = st.session_state.voice_bot.listen_with_sounddevice()
                        
                        if question:
                            # Add user question to chat
                            st.session_state.chat_history.append({"role": "user", "content": question})
                            
                            # Generate AI response
                            with st.spinner("🤔 Thinking and generating response..."):
                                response = st.session_state.voice_bot.generate_response(question)
                                st.session_state.chat_history.append({"role": "assistant", "content": response})
                            
                            st.rerun()
                        else:
                            st.error("❌ Could not capture voice. Please try again.")
        
        with send_col:
            st.markdown("<br>", unsafe_allow_html=True)
            # Send button for text
            if st.button("📤 Send", key="send_text", use_container_width=True, help="Send text question"):
                if text_question.strip():
                    # Add user question to chat
                    st.session_state.chat_history.append({"role": "user", "content": text_question})
                    
                    # Generate AI response
                    with st.spinner("🤔 Thinking and generating response..."):
                        response = st.session_state.voice_bot.generate_response(text_question)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                    
                    # Clear input and refresh
                    st.session_state.main_text_input = ""
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Recording status indicator
        if st.session_state.is_recording:
            st.markdown('''
            <div class="recording-indicator">
                🎤 <strong>RECORDING IN PROGRESS...</strong><br>
                <small>Speak clearly and click "Stop" when finished</small>
            </div>
            ''', unsafe_allow_html=True)
    
    with sidebar_col:
        st.markdown("## 📋 Interview Helper")
        
        # Status indicator
        if st.session_state.voice_bot.microphone_available:
            st.markdown('<div class="status-ready">✅ Microphone Ready</div>', unsafe_allow_html=True)
        else:
            st.error("❌ Microphone Not Available")
        
        st.markdown("### 🎯 How to Use:")
        st.markdown("""
        **Voice Input**: 
        - Click "Start" → Speak → Click "Stop"
        
        **Text Input**: 
        - Type question → Click "Send"
        
        **Quick Start**: 
        - Use sample questions below
        """)
        
        st.markdown("### 💡 Sample Questions:")
        sample_questions = [
            "What should we know about your life story?",
            "What's your #1 superpower?",
            "What are your top 3 growth areas?",
            "What misconception do people have about you?",
            "How do you push your boundaries?"
        ]
        
        for i, question in enumerate(sample_questions):
            if st.button(f"💭 {question[:30]}...", key=f"sample_{i}", use_container_width=True):
                # Add to chat history
                st.session_state.chat_history.append({"role": "user", "content": question})
                
                # Generate response
                with st.spinner("🤔 Generating response..."):
                    response = st.session_state.voice_bot.generate_response(question)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                
                st.rerun()
        
        # Controls section
        st.markdown("### ⚙️ Controls:")
        
        if st.button("🗑️ Clear Chat", key="clear_chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
        
        # Technical info
        st.markdown("### 🔧 Technical Info:")
        st.markdown(f"""
        - **AI Model**: Gemini 1.5 Flash
        - **Speech Recognition**: Google Speech API
        - **Audio**: SoundDevice Library
        - **Status**: {'✅ All Systems Ready' if st.session_state.voice_bot.microphone_available else '⚠️ Voice Limited'}
        """)
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
                method = getattr(st.session_state.voice_bot, 'microphone_method', 'speech_recognition')
                st.success(f"✅ Microphone ready (using {method})")
                
                col1, col2 = st.columns([2, 1])
                with col1:
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
                
                with col2:
                    if method == "sounddevice":
                        st.info("🎙️ Click to record 5 seconds of audio")
                    else:
                        st.info("🎙️ Click and speak your question")
            else:
                st.warning("🎙️ Live microphone not available. Use audio file upload below.")
        
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
        
        # with voice_tab3:
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