# 📓 Data Science Notes

## 🐍 Creating a Virtual Environment in Python

### ✅ Step 1: Create the Environment

```bash
python -m venv <env_name>
```

* This command creates a virtual environment in a folder named `<env_name>`.

---

### ▶️ Step 2: Activate the Environment

#### 🔹 On Linux/macOS:

```bash
source <env_name>/bin/activate
```

#### 🔹 On Windows:

```bash
<env_name>\Scripts\activate
```

> ⚠️ Note: Make sure you’re using the correct path separator (`/` for Unix, `\` for Windows).

---

### ❌ Step 3: Deactivate the Environment

```bash
deactivate
```

* This command exits the virtual environment and returns to the global Python environment.

---

✅ **Tip**: Always activate your environment before installing packages for a project.

