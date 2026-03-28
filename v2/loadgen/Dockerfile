FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8089

CMD ["locust", "-f", "locustfile.py", "--host=http://frontend-service:8001", "--web-host=0.0.0.0"]
