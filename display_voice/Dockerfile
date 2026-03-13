FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update && apt-get install -y wget unzip && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000


ENTRYPOINT ["/entrypoint.sh"]
 
CMD ["python", "main.py"]
