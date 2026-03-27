from locust import HttpUser, task, between

class SystemUser(HttpUser):
    wait_time = between(0.1, 0.5)
    host = "http://frontend-service:8080"

    @task(100)
    def healthy_traffic(self):
        """
        Generate infinite, fast-paced constant baseline of healthy HTTP traffic.
        Ensures Jaeger and Loki have background traces resolving to 200 OK.
        """
        self.client.get("/process", name="healthy_traffic")

    @task(1)
    def chaos_trigger(self):
        """
        Explicit trigger that specifically invokes the chaos endpoint.
        Extremely low weighting (1%) to occasionally halt the backend
        and trip the Prometheus latency thresholds.
        """
        self.client.get("http://payment-service:8080/fault/timeout", name="chaos_trigger")
