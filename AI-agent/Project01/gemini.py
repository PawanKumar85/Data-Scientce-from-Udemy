import os
import json
import google.generativeai as genai

HISTORY_FILE = "chatHistory.json"

class GeminiCaller:
    def __init__(self, api_env_var, model_name="gemini-2.5-pro"):
        self.api_key = os.getenv(api_env_var)
        if not self.api_key:
            raise ValueError(f"❌ API key for '{api_env_var}' not found in .env file.")
        self.model_name = model_name
        genai.configure(api_key=self.api_key)

    def call(self, prompt):
        """Send a prompt to Gemini and save the response to history."""
        try:
            gemini_model = genai.GenerativeModel(self.model_name)
            response = gemini_model.generate_content(prompt)

            if response.candidates and response.candidates[0].content.parts:
                output_text = response.candidates[0].content.parts[0].text
                self._save_history(prompt, output_text)
                return output_text
            else:
                finish_reason = (
                    response.candidates[0].finish_reason
                    if response.candidates else "unknown"
                )
                return f"⚠️ No text returned. Finish reason: {finish_reason}"

        except Exception as e:
            return f"❌ Error during Gemini call: {str(e)}"

    def _save_history(self, prompt, output):
        """Append prompt and response to JSON history file."""
        entry = {"prompt": prompt, "response": output}

        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = []
        else:
            data = []

        data.append(entry)

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
