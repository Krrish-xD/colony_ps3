import time
import requests
from locust import HttpUser, task, between

class MicroserviceUser(HttpUser):
    wait_time = between(0.5, 2)

    def _track_request(self, name, url):
        start_time = time.time()
        try:
            response = requests.get(url)
            response_time = int((time.time() - start_time) * 1000)
            if response.status_code >= 400:
                self.environment.events.request.fire(
                    request_type="GET",
                    name=name,
                    response_time=response_time,
                    response_length=len(response.content),
                    exception=Exception(f"HTTP {response.status_code}: {response.text}"),
                    context={}
                )
            else:
                self.environment.events.request.fire(
                    request_type="GET",
                    name=name,
                    response_time=response_time,
                    response_length=len(response.content),
                    exception=None,
                    context={}
                )
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="GET",
                name=name,
                response_time=response_time,
                response_length=0,
                exception=e,
                context={}
            )

    @task(5)
    def full_chain_via_frontend(self):
        """frontend -> auth -> catalog -> inventory"""
        self.client.get("/process", name="frontend-service /process")

    @task(3)
    def cart_flow(self):
        """cart -> catalog -> inventory"""
        self._track_request("cart-service /process", "http://cart-service:8004/process")

    @task(2)
    def payment_flow(self):
        """payment -> notification"""
        self._track_request("payment-service /process", "http://payment-service:8006/process")

    @task(2)
    def shipping_flow(self):
        """shipping -> inventory"""
        self._track_request("shipping-service /process", "http://shipping-service:8007/process")

    @task(1)
    def recommendation_flow(self):
        """recommendation -> catalog -> inventory"""
        self._track_request("recommendation-service /process", "http://recommendation-service:8008/process")
