import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()

print("Testing vLLM connection to:", os.getenv("VLLM_BASE_URL", "http://100.69.153.16:8020/v1"))
vllm_llm = LLM(
    model="openai/qwen3.6-27b-autoround",
    base_url=os.getenv("VLLM_BASE_URL", "http://100.69.153.16:8020/v1"),
    api_key="sk-no-key",
)

try:
    response = vllm_llm.call(messages=[{"role": "user", "content": "Hello! Just testing the connection."}])
    print("\nSuccess! Response from model:")
    print(response)
except Exception as e:
    print(f"\nError connecting to vLLM: {e}")
