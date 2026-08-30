from transformers import AutoTokenizer,AutoModelForSequenceClassification


model="BAAI/bge-reranker-base"


AutoTokenizer.from_pretrained(model)

AutoModelForSequenceClassification.from_pretrained(model)