from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    description: str | None = None


@app.post("/items/")
def create_item(item: Item):
    return {"item": item}


@app.get("/")
def read_root():
    return {
        "message" : "Welcome to FastAPI Server"
    }
    
@app.get("/user/{user_name}")
def user_name(user_name: str):
    return {
        "message" : f"Hello, {user_name}. Welcome to FastAPI server"
    }