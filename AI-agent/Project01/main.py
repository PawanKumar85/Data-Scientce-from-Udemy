from gemini import GeminiCaller
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    gemini = GeminiCaller(api_env_var="GEMINI_API_KEY")
    while True:
        prompt = input("Enter your prompt: ").strip()
        if prompt.lower() in ["exit", "quit", "clear"]:
            print("👋 Exiting Gemini prompt loop.")
            break

        if prompt:
            result = gemini.call(prompt)
            print(result)
