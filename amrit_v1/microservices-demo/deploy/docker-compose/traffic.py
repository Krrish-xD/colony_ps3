from locust import HttpUser, task, between

class FakeShopper(HttpUser):
    # This tells the fake shopper to pause for 1 to 3 seconds between clicks
    wait_time = between(1, 3) 

    # Task 1: Visit the front doors
    @task(2)
    def view_frontpage(self):
        self.client.get("/")

    # Task 2: Browse the shoe catalog
    @task(1)
    def view_catalogue(self):
        self.client.get("/category.html")