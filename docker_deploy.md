Build: docker build -t voice-bot:latest .
Tag: docker tag voice-bot:latest docker.io/YOUR_DOCKERHUB_USER/voice-bot:YOUR_TAG
Push: docker push docker.io/YOUR_DOCKERHUB_USER/voice-bot:YOUR_TAG
Deploy in Render using “Existing Image” with that Image URL and set GEMINI_API_KEY.

docker tag voice-bot:latest docker.io/viveknaidu007/voice-bot:ver3.3

docker push docker.io/viveknaidu007/voice-bot:ver3.3