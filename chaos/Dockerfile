FROM python:3.11-slim

WORKDIR /mnt/locust

COPY locustfile.py .

RUN pip install --no-cache-dir locust

# Run locust in headless mode, with 10 users and a spawn rate of 1 user/sec.
# Pointing to frontend-service as default host.
CMD ["locust", "-f", "locustfile.py", "--headless", "-u", "10", "-r", "1", "--host=http://frontend-service:8080"]
