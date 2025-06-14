# 📘 Python Basics – Syntax and Semantics

## 🧠 What is Syntax and Semantics?

* **Syntax**: The *structure* or *rules* that define how Python code must be written (like grammar in English).
* **Semantics**: The *meaning* of that structure—what the code actually does when it runs.

---

## 🟦 1. Python Syntax: Rules of Writing Code

### 🔹 a. Indentation

Python uses **indentation** (whitespace) to define blocks of code (no `{}` like other languages).

```python
if True:
    print("This is indented")  # This line is part of the if-block
```

> ❌ Wrong:

```python
if True:
print("This will cause IndentationError")
```

---

### 🔹 b. Comments

Used to explain code. Not executed.

```python
# This is a single-line comment
```

---

### 🔹 c. Variables and Assignment

```python
x = 10
name = "Alice"
```

* No need to declare type explicitly.
* Python is dynamically typed.

---

### 🔹 d. Print Statement

```python
print("Hello, World!")
```

Used to display output.

---

### 🔹 e. Input Statement

```python
user_input = input("Enter your name: ")
```

---

## 🟩 2. Python Semantics: Meaning of the Code

### 🔹 a. Variable Scope

* **Local Scope**: Inside a function.
* **Global Scope**: Outside all functions.

```python
x = 5  # Global

def func():
    y = 10  # Local
```

---

### 🔹 b. Mutable vs Immutable

* **Mutable**: Can be changed (e.g., `list`, `dict`)
* **Immutable**: Cannot be changed (e.g., `int`, `str`, `tuple`)

---

### 🔹 c. Data Types

```python
int, float, str, bool, list, tuple, dict, set
```

---

### 🔹 d. Control Flow

```python
# if-else
if x > 5:
    print("Greater")
else:
    print("Smaller or Equal")

# loops
for i in range(3):
    print(i)

while x > 0:
    x -= 1
```

---

### 🔹 e. Functions

```python
def greet(name):
    return "Hello " + name
```

---

### 🔹 f. Exception Handling

```python
try:
    val = int("abc")
except ValueError:
    print("Invalid conversion")
```

---

