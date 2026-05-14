from fastapi import FastAPI
from .db import get_db


app = FastAPI()








#just boilerplate

@app.post("/order")
def create_order(order: dict):
    return {"message": "Order created", "order": order}

@app.get("/order/{order_id}")
def read_order(order_id: str):
    return {"order": f"This is your order with ID: {order_id}"}

@app.put("/order/{order_id}")
def update_order(order_id: str, order: dict):
    return {"message": "Order updated", "order_id": order_id, "order": order}

@app.delete("/order/{order_id}")
def cancel_order(order_id: str):
    return {"message": "Order deleted", "order_id": order_id}