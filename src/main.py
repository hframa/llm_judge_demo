import os
from dotenv import load_dotenv
# from google import genai  # Commented out to use mock
from src.mock_client import MockClient
from src.wrapper import LimitedClient

load_dotenv()

def main():
    # api_key = os.getenv("GEMINI_API_KEY")
    # if not api_key:
    #     print("Error: GEMINI_API_KEY not found in environment.")
    #     return

    # base_client = genai.Client(api_key=api_key)
    base_client = MockClient(api_key="mock-key")
    client = LimitedClient(base_client)
    
    print("Running 5 requests to test RPM limit (set to 3)...")
    for i in range(5):
        try:
            print(f"Request {i+1}...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Say 'Hello world' for request number {i+1}."
            )
            print(f"Response {i+1}: {response.text.strip()}")
        except Exception as e:
            print(f"An error occurred on request {i+1}: {e}")


if __name__ == "__main__":
    main()
