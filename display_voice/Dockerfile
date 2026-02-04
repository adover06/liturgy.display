FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update && apt-get install -y portaudio19-dev python3-dev libasound-dev python3-pip libasound2-dev alsa-utils wget unzip && rm -rf /var/lib/apt/lists/*  

RUN pip install -r requirements.txt

COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000


ENTRYPOINT ["/entrypoint.sh"]
 
CMD ["python", "main.py"]
