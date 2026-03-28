FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install  -r requirements.txt

COPY . .

EXPOSE 8089

CMD ["locust", "-f", "locustfile.py", "--host=http://frontend-service:8001", "--web-host=0.0.0.0"]
