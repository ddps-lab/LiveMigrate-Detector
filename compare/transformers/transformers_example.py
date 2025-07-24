from transformers import AutoTokenizer, AutoModel, pipeline
import torch
import time

tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
model = AutoModel.from_pretrained('bert-base-uncased')

sentiment_pipeline = pipeline(
    'sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english')

texts = [
    "This is a great day!",
    "I love machine learning.",
    "The weather is terrible today.",
    "Python programming is fun.",
    "Transformers are powerful models."
]

while True:
    for text in texts:
        inputs = tokenizer(text, return_tensors='pt',
                           padding=True, truncation=True)

        with torch.no_grad():
            outputs = model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)

        sentiment = sentiment_pipeline(text)[0]

        print(f"Text: {text}", flush=True)
        print(f"Embedding shape: {embeddings.shape}", flush=True)
        print(
            f"Sentiment: {sentiment['label']} ({sentiment['score']:.3f})", flush=True)
        print("---", flush=True)

    batch_texts = texts[:3]
    batch_inputs = tokenizer(
        batch_texts, return_tensors='pt', padding=True, truncation=True)

    with torch.no_grad():
        batch_outputs = model(**batch_inputs)
        batch_embeddings = batch_outputs.last_hidden_state.mean(dim=1)

    print(f"Batch processing: {batch_embeddings.shape}", flush=True)

    time.sleep(5)
