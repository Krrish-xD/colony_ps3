from locust import HttpUser, task, between

class SockShopUser(HttpUser):
    wait_time = between(1, 5)
    host = "http://edge-router:80"

    @task(3)
    def view_catalog(self):
        self.client.get("/category.html")

    @task(1)
    def view_item(self):
        self.client.get("/detail.html?id=3395a43e-2d88-40de-b95f-e00e1502085b")
        
    @task(1)
    def index(self):
        self.client.get("/")

    @task(2)
    def basket(self):
        self.client.get("/basket.html")
