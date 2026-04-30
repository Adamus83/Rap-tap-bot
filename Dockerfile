FROM python:3.11-slim
WORKDIR /app
COPY bot.py .
RUN pip install pyrogram==2.0.106 tgcrypto
CMD ["python", "bot.py"]
