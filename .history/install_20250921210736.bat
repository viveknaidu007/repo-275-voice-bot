@echo off
echo Installing Voice Bot Dependencies...
echo.

REM Install main requirements first
echo Installing main requirements...
pip install -r requirements.txt

REM Try to install PyAudio with different methods
echo.
echo Attempting to install PyAudio...

REM Method 1: Try direct wheel installation for Windows
echo Method 1: Installing PyAudio wheel for Windows...
pip install https://files.pythonhosted.org/packages/c7/c0/13e70b279d6de7b76970bf2d69baae75c9f8e4bf35d4a89c50c8d24a18c3/PyAudio-0.2.11-cp310-cp310-win_amd64.whl

REM If that fails, try conda if available
if %errorlevel% neq 0 (
    echo Method 1 failed. Trying conda...
    conda install -c anaconda pyaudio -y
    
    REM If conda also fails, inform user
    if %errorlevel% neq 0 (
        echo.
        echo ===============================================
        echo WARNING: PyAudio installation failed
        echo ===============================================
        echo The voice bot will work with limited functionality:
        echo - Text input will work perfectly
        echo - Audio file upload will work  
        echo - Live microphone may not work
        echo.
        echo To fix this later, try:
        echo 1. conda install pyaudio
        echo 2. Use Windows Subsystem for Linux (WSL)
        echo 3. Use the web audio recorder feature
        echo ===============================================
    )
)

echo.
echo Installation complete!
echo Run the app with: streamlit run app.py
pause