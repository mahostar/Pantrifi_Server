import os
import time
from dotenv import load_dotenv
from google import genai

class GeminiAPIManager:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Load API keys from environment
        self.api_keys = self._load_api_keys()
        self.max_retries_per_key = 3
        self.retry_delay = 2  # seconds
        
        if not self.api_keys:
            raise ValueError("ERROR: No GEMINI_API_KEY found in .env file")
        
        print(f"INFO: Loaded {len(self.api_keys)} API key(s)")
        
    def _load_api_keys(self):
        """Load API keys from environment variables."""
        api_keys = []
        
        # Try to load multiple API keys (GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.)
        i = 1
        while True:
            key_name = f"GEMINI_API_KEY_{i}" if i > 1 else "GEMINI_API_KEY"
            api_key = os.getenv(key_name)
            if api_key:
                api_keys.append(api_key)
                i += 1
            else:
                break
        
        return api_keys
    
    def _try_single_key(self, key_index, model, contents, **kwargs):
        """Try a single API key with its own retry attempts."""
        api_key = self.api_keys[key_index]
        client = genai.Client(api_key=api_key)
        
        for attempt in range(1, self.max_retries_per_key + 1):
            try:
                print(f"INFO: Using API key #{key_index + 1} (Attempt {attempt}/{self.max_retries_per_key})")
                
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    **kwargs
                )
                
                print(f"SUCCESS: Request completed with API key #{key_index + 1}")
                return response
                
            except Exception as error:
                error_message = str(error)
                print(f"WARNING: API Error (Attempt {attempt}/{self.max_retries_per_key}): {error_message}")
                
                # If this is the last attempt for this key, don't wait
                if attempt < self.max_retries_per_key:
                    # Check if it's a rate limit (429) - if so, wait before retry
                    if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                        wait_time = self.retry_delay * attempt
                        print(f"INFO: Rate limit detected - waiting {wait_time} seconds before retry")
                        time.sleep(wait_time)
                    else:
                        # For other errors, just a short delay
                        time.sleep(1)
        
        print(f"ERROR: API key #{key_index + 1} failed after {self.max_retries_per_key} attempts")
        return None
    
    def generate_content(self, model="gemini-2.5-flash", contents="", **kwargs):
        """Generate content by trying each API key sequentially."""
        
        # Try each API key one by one
        for key_index in range(len(self.api_keys)):
            print(f"\nINFO: Trying API key #{key_index + 1}")
            
            result = self._try_single_key(key_index, model, contents, **kwargs)
            
            if result is not None:
                return result
            
            print(f"INFO: Moving to next API key...")
        
        # If we get here, all keys failed
        raise Exception(f"ERROR: All {len(self.api_keys)} API keys failed after {self.max_retries_per_key} attempts each")

def main():
    """Main function to test the Gemini API with error handling."""
    try:
        # Initialize the API manager
        gemini_manager = GeminiAPIManager()
        
        # Test the connection
        print("\nINFO: Testing Gemini API connection...")
        response = gemini_manager.generate_content(
            model="gemini-2.5-flash",
            contents="Explain how AI works in a few words"
        )
        
        print(f"\nRESPONSE: {response.text}")
        
    except ValueError as e:
        print(f"ERROR: Configuration Error: {e}")
        print("\nINFO: Please add your API keys to the .env file:")
        print("GEMINI_API_KEY=your_first_api_key")
        print("GEMINI_API_KEY_2=your_second_api_key")
        print("GEMINI_API_KEY_3=your_third_api_key")
        print("... (add as many as you want)")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()