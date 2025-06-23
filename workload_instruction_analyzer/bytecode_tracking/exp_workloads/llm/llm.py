from llama_cpp import Llama
import time
llm = Llama(
    model_path="./Qwen3-0.6B-Q8_0.gguf",
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
