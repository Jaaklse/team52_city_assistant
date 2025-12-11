FROM python:3.12

WORKDIR /app

# RUN apt-get update && apt-get install -y --no-install-recommends \
#         curl \
#     && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Устанавливаем зависимости без компиляции (быстрее)
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
