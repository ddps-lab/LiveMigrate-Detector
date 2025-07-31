from fastapi import FastAPI
import uvicorn
import requests
import time
import threading

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World", "timestamp": time.time()}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q, "timestamp": time.time()}


@app.post("/items/")
async def create_item(name: str, price: float):
    return {"name": name, "price": price, "created_at": time.time()}


def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")


def make_requests():
    time.sleep(2)
    while True:
        try:
            response1 = requests.get('http://127.0.0.1:8001/')
            print(f"Root: {response1.json()}", flush=True)

            response2 = requests.get('http://127.0.0.1:8001/items/123?q=test')
            print(f"Item: {response2.json()}", flush=True)

            response3 = requests.post('http://127.0.0.1:8001/items/',
                                      params={'name': 'laptop', 'price': 999.99})
            print(f"Created: {response3.json()}", flush=True)
        except Exception as e:
            print(f"Request failed: {e}", flush=True)

        time.sleep(5)


server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

make_requests()
