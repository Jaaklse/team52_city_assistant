from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F


MODEL_NAME = "cointegrated/rubert-tiny-toxicity"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
toxic_roots = ["дура", "глуп", "неумн", "кончен", "дрян"]
def check_toxicity(text):
    text = text.lower()
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        logits = model(**inputs).logits

    toxic_prob = F.softmax(logits[:, :2], dim=1)[0][1].item()
    for toxic in toxic_roots:
        if (toxic in text):
            toxic_prob += 0.6
    return {"toxic": f"{toxic_prob:.10f}"}
