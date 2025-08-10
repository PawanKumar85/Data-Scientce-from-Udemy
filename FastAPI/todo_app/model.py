from pydantic import BaseModel
from typing import Optional

class Todo(BaseModel):
    name : str
    completed: bool = False
    description : Optional[str] = None
    
class TodoUpdate(BaseModel):
    name: Optional[str] = None
    completed : Optional[bool] = None
    description : Optional[str] = None 