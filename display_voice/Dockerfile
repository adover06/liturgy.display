FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update && apt-get install -y portaudio19-dev python3-dev libasound-dev python3-pip alsa-base alsa-utils

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
 
CMD ["python", "main.py"]
