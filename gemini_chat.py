import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env file
load_dotenv()

class GeminiChat:
    def __init__(self):
        # Get API key from environment variable
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables. Please check your .env file.")
        
        # Initialize the client directly with API key
        self.client = genai.Client(api_key=self.api_key)
        
        # Default system prompt
        self.system_prompt = "You are a helpful AI assistant. Be friendly and informative."
        
        print("🤖 Gemini 2.5 Flash Chat initialized successfully!")
        print(f"📝 Current system prompt: {self.system_prompt}")
    
    def set_system_prompt(self, prompt):
        """Set a custom system prompt"""
        self.system_prompt = prompt
        print(f"✅ System prompt updated: {prompt}")
    
    def chat(self, message):
        """Send a message to Gemini and get response"""
        try:
            # Combine system prompt with user message
            full_prompt = f"System: {self.system_prompt}\n\nUser: {message}"
            
            print("\n🤔 Gemini is thinking...")
            
            # Generate response (simplified without thinking config)
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt
            )
            
            return response.text
            
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def interactive_chat(self):
        """Start an interactive chat session"""
        print("\n🚀 Starting interactive chat with Gemini 2.5 Flash!")
        print("Commands:")
        print("  /system <prompt> - Change system prompt")
        print("  /quit - Exit chat")
        print("  /help - Show this help")
        print("\n" + "="*50)
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/system '):
                    new_prompt = user_input[8:].strip()
                    if new_prompt:
                        self.set_system_prompt(new_prompt)
                    else:
                        print("❌ Please provide a system prompt after /system")
                    continue
                
                elif user_input == '/quit':
                    print("👋 Goodbye!")
                    break
                
                elif user_input == '/help':
                    print("Commands:")
                    print("  /system <prompt> - Change system prompt")
                    print("  /quit - Exit chat")
                    print("  /help - Show this help")
                    continue
                
                # Regular chat message
                response = self.chat(user_input)
                print(f"\n🤖 Gemini: {response}")
                
            except KeyboardInterrupt:
                print("\n👋 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")

def main():
    """Main function to run the chat"""
    try:
        # Initialize the chat
        chat = GeminiChat()
        
        # Send a greeting message
        print("\n🎉 Let's start with a greeting!")
        greeting_response = chat.chat("Hi there!")
        print(f"\n🤖 Gemini: {greeting_response}")
        
        # Start interactive chat
        chat.interactive_chat()
        
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        print("Please make sure your .env file contains: GEMINI_API_KEY=your_api_key_here")

if __name__ == "__main__":
    main()