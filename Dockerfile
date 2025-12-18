FROM python:3.9-alpine

# Install FFmpeg and Fonts
# ttf-dejavu provides standard fonts needed for subtitles
RUN apk add --no-cache ffmpeg ttf-dejavu

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

# Use Gunicorn for better stability than the dev server
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "app:app", "--timeout", "1000"]
