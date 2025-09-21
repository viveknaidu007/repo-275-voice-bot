#!/bin/bash
echo "🤖 Starting Voice Bot Application..."
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create a .env file with your GEMINI_API_KEY"
    echo ""
    echo "Example .env content:"
    echo "GEMINI_API_KEY=your_actual_api_key_here"
    echo ""
    exit 1
fi

# Check if GEMINI_API_KEY is set
if grep -q "your_gemini_api_key_here" .env; then
    echo "❌ Please update your GEMINI_API_KEY in the .env file"
    echo "Get your key from: https://makersuite.google.com/app/apikey"
    echo ""
    exit 1
fi

echo "✅ Configuration looks good!"
echo "🚀 Starting Streamlit application..."
echo ""

# Start the application
streamlit run app.py