import re
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

lm = WordNetLemmatizer()
stop_words = set(stopwords.words("english"))

def preprocess_text(text):
    review = re.sub(r"[^a-zA-Z0-9]", " ", text)   # keep words/numbers only
    review = review.lower()
    review = review.split()
    review = [lm.lemmatize(w) for w in review if w not in stop_words]
    return " ".join(review)
