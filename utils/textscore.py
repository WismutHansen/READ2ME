from transformers import AutoTokenizer, AutoModelForSequenceClassification

def score_text(text):
    try:
        tokenizer = AutoTokenizer.from_pretrained("HuggingFaceTB/fineweb-edu-classifier")
        model = AutoModelForSequenceClassification.from_pretrained(
            "HuggingFaceTB/fineweb-edu-classifier"
        )
        inputs = tokenizer(text, return_tensors="pt", padding="longest", truncation=True)
        outputs = model(**inputs)
        logits = outputs.logits.squeeze(-1).float().detach().numpy()
        score = logits.item()

        rounded_score = round(score, 3)  # Round the score to the third decimal point
        
        return rounded_score 
                    
    except Exception as e:
        logging.error(f"Failed to text scoring model: {e}")
        return False
