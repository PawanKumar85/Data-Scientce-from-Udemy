import psycopg2.pool
from flask import Flask,request,jsonify
import psycopg2
from psycopg2 import pool
import os

class TodoApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.db_pool = psycopg2.pool.SimpleConnectionPool(
            1,20,
            user = "todo_user",
            password = "todo_password",
            host = "localhost",
            port = "5432",
            database = "todo_db"
        )
        self.init_db()
        self.setup_routes()

    def init_db(self):
        connection = self.db_pool.getconn()
        try:
            with connection.cursor() as curr:
                curr.execute("""
                    CREATE TABLE IF NOT EXISTS todos(
                        id SERIAL PRIMARY KEY,
                        task VARCHAR(100) NOT NULL,
                        status BOOLEAN DEFAULT FALSE
                    )
                """)
            connection.commit() 
            print("Table Create Successfully")
        except Exception as e:
            print("Error : ",e)
        finally:
            self.db_pool.putconn(connection)

    def setup_routes(self):
        app = self.app
        db_pool = self.db_pool

        # Root
        @app.route("/")
        def root():
            return jsonify({
            "Success" : "Server is running on PORT 5000"
            }),200

        # Create : Add New Item into DB
        @app.route("/todos",methods=['POST'])
        def create_todo():
            data = request.get_json()
            print("Data : ",data)

            task = data.get("task")

            if not task:
                return jsonify({
                    "error" : "Task is Required."
                }),400
            

            connection = db_pool.getconn()
            try:
                with connection.cursor() as curr:
                    curr.execute("INSERT INTO todos (task) VALUES (%s) RETURNING id", (task,))
                    todo_id = curr.fetchone()[0]
                connection.commit()
                return jsonify({
                    "id" : todo_id,
                    "task" : task,
                    "status" : False
                }),201
            except Exception as e:
                return jsonify({
                    "error" : f"{e}"
                }),400
            finally:
                db_pool.putconn(connection)

        # Read : Read All Items from DB 
        @app.route("/todos",methods=['GET'])
        def read_todo():
            connection = db_pool.getconn()
            try:
                with connection.cursor() as curr:
                    curr.execute("SELECT id,task,status from todos")
                    todos = curr.fetchall()
                return jsonify(
                    [
                        {"id": id, "task": task, "status": status} for id, task, status in todos
                    ]
                ),200
            except Exception as e:
                return jsonify({
                    "error" : f"{e}"
                }),400 
            finally:
                db_pool.putconn(connection)

        # Read : Read Item By Id from DB
        @app.route("/todos/<int:id>",methods=['GET'])
        def read_todo_single(id):
            connection = db_pool.getconn()
            try:
                with connection.cursor() as curr:
                    curr.execute("SELECT id,task,status from todos WHERE id = %s",(id,))

                    todo = curr.fetchone()

                    if not todo:
                        return jsonify({
                            "error": f"Todo with ID = {id} not found"
                        }), 404

                    todo_id, task, status = todo
                    return jsonify({
                        "id": todo_id,
                        "task": task,
                        "status": status
                    }), 200
            except Exception as e:
                return jsonify({
                    "error" : f"{e}"
                }),400 
            finally:
                db_pool.putconn(connection)

        # Update : Update Item by Id into DB
        @app.route("/todos/<int:id>",methods=['PUT'])
        def update_todo(id):
            data = request.get_json()
            task = data.get("task")
            status = data.get("status")

            if not task:
                return jsonify(
                    {"error": "Task required"}
                ), 400
            
            if status is not None:
                status = bool(status)

            connection = db_pool.getconn()

            try:
                with connection.cursor() as curr:
                    curr.execute("SELECT id FROM todos WHERE id = %s",(id,))

                    if not curr.fetchone():
                        return jsonify({
                            "error" : "Todo Not Found"
                        }),404
                    
                    update_query = "UPDATE todos SET "
                    params = []

                    if task is not None:
                        update_query += "task = %s, "
                        params.append(task)
                    if status is not None:
                        update_query += "status = %s, "
                        params.append(status)
                    update_query = update_query.rstrip(", ") + " WHERE id = %s"
                    params.append(id)

                    print("Update Query :",update_query)
                    print("Params :", ", ".join(map(str, params)))
                    
                    curr.execute(update_query, params)
                connection.commit()
                return jsonify({
                    "id": id, 
                    "task": task, 
                    "status": status
                    }),200
            except Exception as e:
                return jsonify({
                    "Error " :  f"{e}"
                }),40
            finally:
                db_pool.putconn(connection)

        # Delete : Delete Item by Id into DB
        @app.route("/todos/<int:id>",methods=['DELETE'])
        def delete_todo(id):
            connection = db_pool.getconn()
            try:
                with connection.cursor() as curr:
                    curr.execute("SELECT id FROM todos WHERE id = %s", (id,))

                    if not curr.fetchone():
                        return jsonify({"error": "Todo not found"}), 404
                    
                    curr.execute("DELETE FROM todos WHERE id = %s",(id,))
                connection.commit()
                return jsonify(
                    {
                        "message": "Todo deleted"
                    }
                    ),200
            except Exception as e:
                return jsonify({
                    "Error" : f"{e}"
                }),400
            finally:
                db_pool.putconn(connection)

        # Toggle : 
        @app.route("/todos/<int:id>/toggle", methods=['PATCH'])
        def toggle_status(id):
            connection = db_pool.getconn()
            try:
                with connection.cursor() as curr:
                    curr.execute("UPDATE todos SET status = NOT status WHERE id = %s RETURNING id, task, status", (id,))
                    updated = curr.fetchone()
                    if not updated:
                        return jsonify({"error": "Todo not found"}), 404
                connection.commit()
                return jsonify({"id": updated[0], "task": updated[1], "status": updated[2]}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 400
            finally:
                db_pool.putconn(connection)

if __name__ == '__main__':
    todo_app = TodoApp()         
    todo_app.app.run(debug=True)  
