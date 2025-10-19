import os
import cohere
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(".env")

def test_openai():
    print("Testing OpenAI API key...")
    client = OpenAI(
        api_key=os.getenv("OPENAI_LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    )
    
    try:
        models = client.models.list()
        print(f"Success! Found {len(models.data)} models.")
        print("First 5 models:")
        for model in models.data[:5]:
            print(f"- {model.id}")
        return True
    except Exception as e:
        print(f"OpenAI test failed: {str(e)}")
        return False

def test_cohere():
    print("\nTesting Cohere API key...")
    client = cohere.Client(
        api_key=os.getenv("COHERE_API_KEY"),
        base_url=os.getenv("COHERE_BASE_URL")
    )
    
    try:
        response = client.tokenize(text="Hello world", model="command")
        print(f"Success! Tokenized text: {response.tokens}")
        return True
    except Exception as e:
        print(f"Cohere test failed: {str(e)}")
        return False

if __name__ == "__main__":
    openai_ok = test_openai()
    cohere_ok = test_cohere()
    
    print("\nSummary:")
    print(f"OpenAI: {'OK' if openai_ok else 'FAILED'}")
    print(f"Cohere: {'OK' if cohere_ok else 'FAILED'}")
