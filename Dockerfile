FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install pyrogram tgcrypto
CMD ["python", "bot.py"]
