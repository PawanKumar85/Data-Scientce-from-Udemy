import json
import os
from fastapi import FastAPI,HTTPException
from model import Todo,TodoUpdate

app = FastAPI()

DATA_FILE = "todos.json"

# Helper Function
def read_data():
    if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)
    
def write_data(data):
    with open(DATA_FILE,"w") as f:
        json.dump(data,f,indent=4)
        
# Get all the Data's
@app.get("/todos")
def all_data():
    return read_data()

# Get Data By ID
@app.get("/todos/{id}")
def get_data_by_id(id: int):
    todos = read_data()
    if id < 0 or id > len(todos):
        raise HTTPException(status_code = 404,detail = "Todo not found")
    return todos[id]

# Add Todo
@app.post("/todos",status_code = 201)
def add_todo(todo: Todo):
    todos = read_data()
    todos.append(todo.dict())
    write_data(todos)
    return {"message": "Todo added successfully"}


# Update Todo
@app.patch("/todos/{id}")
def update_todo(id : int,todo : TodoUpdate):
    todos = read_data()
    if id < 0 or id >= len(todos):
        raise HTTPException(status_code=404, detail="Todo not found")
    stored_todo = todos[id]
    update_data = todo.dict(exclude_unset=True)
    stored_todo.update(update_data)
    todos[id] = stored_todo
    write_data(todos)
    return {"message": "Todo updated successfully"}

# Delete todo
@app.delete("/todos/{id}")
def delete_todo(id : int):
    todos = read_data()
    if id < 0 or id >= len(todos):
        raise HTTPException(status_code=404, detail="Todo not found")
    deleted = todos.pop(id)
    write_data(todos)
    return {"message": "Todo deleted successfully", "deleted": deleted}



