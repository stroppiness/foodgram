FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN pip install gunicorn==25.3.0
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "foodgram_api.wsgi"]