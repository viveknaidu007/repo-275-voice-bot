# 🤖 Voice Bot

A professional voice-enabled chatbot for AI Agent Team. This application uses Streamlit for the web interface, Google's Gemini AI (hence they have free api keys rather than Chatgpt) for intelligent responses, and speech recognition for voice interactions.

## 🚀 Features

- **Voice Input**: Speak your questions naturally
- **Text Input**: Type questions if you prefer
- **AI-Powered Responses**: Uses Gemini AI to respond 
- **Text-to-Speech**: Hear the responses spoken aloud
- **Professional UI**: Clean, modern Streamlit interface
- **Interview-Ready**: Pre-configured with relevant context

## 🛠️ Technology Stack

- **Frontend**: Streamlit
- **AI Model**: Google Gemini Pro API
- **Speech Recognition**: Google Speech Recognition API
- **Text-to-Speech**: pyttsx3
- **Audio Processing**: PyAudio
- **Environment Management**: python-dotenv

## 📋 Prerequisites

- Python 3.8 or higher
- Microphone access for voice input
- Gemini API key (free from Google AI Studio)
- Internet connection for speech recognition and AI responses

## 🔧 Installation & Setup

### Step 1: Clone the Repository
```bash
git clone https://github.com/viveknaidu007/repo-275-voice-bot.git
cd repo-275-voice-bot
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

**Note for Windows/Conda users**: PyAudio wheels are now available for Python 3.8–3.12. If you still hit build errors, try:
```cmd
pip install --upgrade pip wheel setuptools
pip install pyaudio==0.2.14
```
If using Conda/Anaconda and the above fails, try Conda-forge:
```cmd
conda install -c conda-forge pyaudio
```

### Step 3: Get Your Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the API key

### Step 4: Configure Environment Variables
1. Open the `.env` file in the project root
2. Replace `your_gemini_api_key_here` with your actual Gemini API key:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

### Step 5: Run the Application
```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## 🎯 Usage Guide

### Voice Interaction
1. Click the "🎤 Start Voice Input" button
2. Wait for the "Listening..." indicator
3. Speak your question clearly
4. The bot will process your speech and respond both in text and voice

### Text Interaction
1. Type your question in the text area
2. Click "📤 Send Question"
3. The bot will respond with text 

### Sample Questions
The application includes pre-loaded sample questions such as:
- What should we know about your life story?
- What's your #1 superpower?
- What are the top 3 areas you'd like to grow in?
- What misconception do your coworkers have about you?
- How do you push your boundaries and limits?

## 🎨 User Interface Features

- **Real-time Status Indicators**: Shows when the bot is listening, processing, or ready
- **Chat History**: Maintains conversation history during the session
- **Responsive Design**: Works on desktop and mobile devices
- **Professional Styling**: Clean, modern interface suitable for interviews
- **Clear Navigation**: Intuitive layout with helpful instructions

## 🔍 Technical Details

### Voice Processing Pipeline
1. **Audio Capture**: Uses PyAudio to capture microphone input
2. **Speech-to-Text**: Google Speech Recognition converts audio to text
3. **AI Processing**: Gemini AI generates contextual responses


### AI Context Configuration
The bot is pre-configured with professional context about:
- Software development experience
- AI/ML expertise
- Remote work capabilities
- Problem-solving skills
- Continuous learning mindset

### Error Handling
- Graceful handling of microphone issues
- Network connectivity error management
- API rate limiting protection
- User-friendly error messages

## 🚀 Deployment Options

### Local Development
- Run directly with `streamlit run app.py`
- Ideal for testing and development

### Streamlit Cloud (Recommended for Demo)
1. Push your code to GitHub
2. Connect your repository to [Streamlit Cloud](https://streamlit.io/cloud)
3. Add your Gemini API key to Streamlit Cloud secrets
4. Deploy with one click

### Other Deployment Platforms
- **Heroku**: Add Procfile and requirements for easy deployment
- **Docker**: Containerize the application for consistent deployment
- **AWS/GCP**: Deploy on cloud platforms with proper environment configuration

## 🔒 Security & Privacy

- API keys are stored in environment variables
- No conversation data is permanently stored
- Speech processing happens locally when possible
- Secure HTTPS connections for API calls

## 🐛 Troubleshooting

### Common Issues

**Microphone not working:**
- Check browser permissions for microphone access
- Ensure your microphone is not being used by other applications
- Try refreshing the page

**API Key errors:**
- Verify your Gemini API key is correct in the `.env` file
- Check that your API key has the necessary permissions
- Ensure you haven't exceeded API rate limits

**PyAudio installation issues:**
- On Windows: `pip install pyaudio==0.2.14` (prebuilt wheel)
- On macOS: Install with `brew install portaudio` then `pip install pyaudio`
- On Linux: Install with `sudo apt-get install python3-pyaudio`

If you see `Cannot open include file: 'portaudio.h'`, it means pip is trying to build from source. Use the wheel (`pyaudio==0.2.14`) or install via Conda.


---

