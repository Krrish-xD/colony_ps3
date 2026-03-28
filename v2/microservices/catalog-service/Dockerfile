FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install  -r requirements.txt

EXPOSE 8003

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
