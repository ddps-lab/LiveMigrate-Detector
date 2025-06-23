from llama_cpp import Llama
import time
import os
import requests

MODEL_PATH = "./Qwen3-0.6B-Q8_0.gguf"

# check model exists
if not os.path.exists(MODEL_PATH):
    response = requests.get(
        "https://huggingface.co/unsloth/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q8_0.gguf?download=true")
    with open(MODEL_PATH, "wb") as f:
        f.write(response.content)

llm = Llama(
    model_path=MODEL_PATH,
)

while True:
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "hi? /no_think"}
        ]
    )
    print(response["choices"][0]["message"]["content"])
    time.sleep(5)
