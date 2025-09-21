import streamlit as st
import speech_recognition as sr
import google.generativeai as genai
import os
from dotenv import load_dotenv
import pyttsx3

# Load environment variables
load_dotenv()

# Try to import audio recorder (optional)
AUDIO_RECORDER_AVAILABLE = False
try:
    from streamlit_audio_recorder import audio_recorder
    AUDIO_RECORDER_AVAILABLE = True
except ImportError:
    pass

class VoiceBot:
    def __init__(self):
        """Initialize the Voice Bot with API configuration and components."""
        # Initialize Gemini API
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            st.error("❌ GEMINI_API_KEY not found in environment variables!")
            st.stop()
        
        genai.configure(api_key=api_key)
        
        # Try different model names in order of preference
        model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        self.model = None
        
        for model_name in model_names:
            try:
                self.model = genai.GenerativeModel(model_name)
                st.success(f"✅ Using model: {model_name}")
                break
            except Exception as e:
                st.warning(f"⚠️ Model {model_name} not available: {str(e)}")
                continue
        
        if not self.model:
            st.error("❌ No Gemini models available!")
            st.stop()
        
        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()
        
        # Check microphone availability
        self.microphone_available = self._check_microphone()
        
        # Initialize text-to-speech
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_available = True
        except:
            self.tts_available = False
    
    def _check_microphone(self):
        """Check if microphone is available."""
        try:
            # Test sounddevice
            devices = sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            if input_devices:
                self.microphone_method = 'sounddevice'
                return True
            
            # Fallback to speech_recognition
            with sr.Microphone() as source:
                pass
            self.microphone_method = 'speech_recognition'
            return True
        except Exception as e:
            st.error(f"❌ Microphone error: {str(e)}")
            return False
    
    def listen_with_sounddevice(self, duration=5):
        """Record audio using sounddevice for better compatibility."""
        try:
            sample_rate = 44100
            channels = 1
            
            st.info(f"🎤 Recording for {duration} seconds...")
            
            # Record audio
            audio_data = sd.rec(int(duration * sample_rate), 
                              samplerate=sample_rate, 
                              channels=channels, 
                              dtype=np.float32)
            sd.wait()  # Wait until recording is finished
            
            # Convert to 16-bit PCM
            audio_data = (audio_data * 32767).astype(np.int16)
            
            # Save to temporary WAV file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(channels)
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_data.tobytes())
                
                # Process with speech recognition
                with sr.AudioFile(temp_file.name) as source:
                    audio = self.recognizer.record(source)
                    try:
                        text = self.recognizer.recognize_google(audio)
                        return text
                    except sr.UnknownValueError:
                        st.error("❌ Could not understand audio")
                        return None
                    except sr.RequestError as e:
                        st.error(f"❌ Speech recognition error: {e}")
                        return None
                    finally:
                        # Clean up temp file
                        try:
                            os.unlink(temp_file.name)
                        except:
                            pass
        
        except Exception as e:
            st.error(f"❌ Recording error: {str(e)}")
            return None
    
    def check_microphone_permissions(self):
        """Check and request microphone permissions."""
        try:
            # Test microphone access
            with sr.Microphone() as source:
                st.info("🎤 Testing microphone access...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                st.success("✅ Microphone access granted!")
                return True
        except sr.RequestError as e:
            st.error(f"❌ Microphone service error: {e}")
            return False
        except Exception as e:
            st.error(f"❌ Microphone permission denied or not available: {e}")
            st.warning("🔧 Please check your browser settings to allow microphone access")
            return False
    
    def listen_with_microphone(self, duration=8):
        """Record audio using microphone with proper permission handling."""
        try:
            # Check microphone permissions first
            if not self.check_microphone_permissions():
                return None
            
            with sr.Microphone() as source:
                st.info("🎤 Adjusting for background noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                st.success(f"🎙️ Recording for {duration} seconds... Speak now!")
                
                # Record with timeout
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=duration)
                
                st.info("🔄 Processing your speech...")
                
                # Process the audio
                try:
                    text = self.recognizer.recognize_google(audio)
                    return text
                except sr.UnknownValueError:
                    st.error("❌ Could not understand the audio. Please speak more clearly.")
                    return None
                except sr.RequestError as e:
                    st.error(f"❌ Speech recognition service error: {e}")
                    return None
                    
        except sr.WaitTimeoutError:
            st.error("❌ No speech detected. Please try again.")
            return None
        except Exception as e:
            st.error(f"❌ Recording error: {str(e)}")
            st.warning("💡 Tip: Make sure your microphone is connected and browser has permission")
            return None
    
    def start_recording_session(self):
        """Start a recording session - just sets the flag."""
        return True
    
    def process_voice_recording(self):
        """Process voice recording with proper microphone handling."""
        return self.listen_with_microphone(duration=10)  # 10 second max recording
    
    def generate_response(self, question):
        """Generate response using Gemini API."""
        try:
            # Enhanced prompt for interview context
            prompt = f"""
            You are a job candidate being interviewed for the 100x AI Agent Team position. 
            You should answer as yourself (the candidate) in a professional, authentic, and engaging manner.
            
            Be specific, provide examples, and show enthusiasm for the role.
            Keep responses conversational but professional (2-4 sentences typically).
            
            Interview Question: {question}
            
            Your Response:
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            # Fallback response for API errors
            fallback_responses = {
                "life story": "I'm a passionate AI developer with a background in machine learning and software engineering. I've been working on various AI projects and am excited about the opportunity to contribute to innovative AI agent development at 100x.",
                "superpower": "My superpower is breaking down complex technical problems into manageable solutions and communicating them clearly to both technical and non-technical stakeholders.",
                "growth": "I'm particularly interested in growing my expertise in large language models, improving my system design skills, and learning more about production AI deployment at scale.",
                "misconception": "People sometimes think I'm purely technical, but I actually enjoy the collaborative and creative aspects of AI development, especially working with cross-functional teams.",
                "boundaries": "I push my boundaries by taking on projects outside my comfort zone, contributing to open-source AI projects, and staying current with the latest research in AI and machine learning."
            }
            
            # Simple keyword matching for fallback
            question_lower = question.lower()
            for key, response in fallback_responses.items():
                if key in question_lower:
                    return response
            
            return f"Thank you for that question. I believe my experience and passion for AI development make me a strong candidate for this position. Could you tell me more about what you're looking for in this role?"

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
            # Professional voice recording button
            if st.button("🎤 Record Voice", key="voice_record", use_container_width=True, help="Click to record your interview question"):
                # Process voice recording immediately
                with st.spinner("🎤 Initializing microphone..."):
                    question = st.session_state.voice_bot.process_voice_recording()
                    
                    if question:
                        st.success(f"📝 Voice captured: \"{question}\"")
                        # Add user question to chat
                        st.session_state.chat_history.append({"role": "user", "content": question})
                        
                        # Generate AI response
                        with st.spinner("🤔 Generating response..."):
                            response = st.session_state.voice_bot.generate_response(question)
                            st.session_state.chat_history.append({"role": "assistant", "content": response})
                        
                        st.rerun()
                    else:
                        st.error("❌ Voice recording failed. Please try again or use text input.")
        
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
    
    with sidebar_col:
        st.markdown("## 📋 Interview Helper")
        
        # Status indicator
        if st.session_state.voice_bot.microphone_available:
            st.markdown('<div class="status-ready">✅ Microphone Ready</div>', unsafe_allow_html=True)
        else:
            st.error("❌ Microphone Not Available")
        
        # Microphone test button
        if st.button("🔧 Test Microphone", key="test_mic", use_container_width=True):
            with st.spinner("Testing microphone access..."):
                if st.session_state.voice_bot.check_microphone_permissions():
                    st.success("🎤 Microphone test successful!")
                    st.session_state.voice_bot.microphone_available = True
                else:
                    st.error("❌ Microphone test failed")
                    st.session_state.voice_bot.microphone_available = False
        
        st.markdown("### 🎯 How to Use:")
        st.markdown("""
        **🎤 Voice Input**: 
        - Click "Record Voice" button
        - Allow microphone permission when prompted
        - Speak your question clearly (max 10 seconds)
        - AI will process and respond
        
        **⌨️ Text Input**: 
        - Type your question in the text area
        - Click "Send" to get response
        
        **⚡ Quick Start**: 
        - Use sample questions below for testing
        """)
        
        # Microphone permission notice
        if not st.session_state.voice_bot.microphone_available:
            st.warning("""
            **📢 Microphone Setup Required:**
            1. Allow microphone access when prompted by your browser
            2. Check system microphone settings
            3. Refresh the page if needed
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

if __name__ == "__main__":
    main()