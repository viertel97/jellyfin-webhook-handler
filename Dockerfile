FROM python:3.11-slim-buster

COPY . .

COPY requirements.txt .

ENV IS_CONTAINER=True

EXPOSE 80

CMD ["python", "main.py"]




