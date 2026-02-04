import asyncio
import os
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel
from dotenv import load_dotenv

async def test_ai():
    load_dotenv()
    
    api_key = os.getenv("AI_API_KEY")
    model_name = os.getenv("AI_MODEL", "llama-3.1-70b-versatile")
    
    print(f"Testing AI with model: {model_name}")
    print(f"API Key present: {'Yes' if api_key else 'No'}")
    
    try:
        model = GroqModel(
            model_name=model_name,
            api_key=api_key
        )
        agent = Agent(model=model)
        
        print("Running agent...")
        result = await agent.run("Say hello")
        print(f"Result: {result.data}")
        print("AI check PASSED")
    except Exception as e:
        print(f"AI check FAILED: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_ai())
