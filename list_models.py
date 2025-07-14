import os
import openai

# Get the API key from the environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("OPENAI_API_KEY environment variable not set. Please set it before running the script.")
else:
    try:
        client = openai.OpenAI(api_key=api_key)
        models = client.models.list()
        print("✅ Successfully connected to OpenAI API. Available models:")
        for model in sorted(models.data, key=lambda x: x.id):
            print(f"- {model.id}")
    except Exception as e:
        print(f"❌ An error occurred while connecting to OpenAI API: {e}")
