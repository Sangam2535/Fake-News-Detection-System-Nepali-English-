import pandas as pd

# Load stopwords from CSV once
stopwords_df = pd.read_csv(r"C:\Users\Dell\fake-news-detector\data\nepali\stopwords.csv", header=None)
custom_stopwords = set(stopwords_df[0].tolist())

def custom_stem(word):
    suffixes = [
        'लाई','बाट','ता','ले','बाट', 'बाहेक', 'बाहिर', 'बाहिरपट्टी', 'भित्र', 'का', 'करिब', 'को', 'छ', 'छिन्',
        'जोड', 'ते', 'लागि', 'लाई', 'माथि', 'मन्तिर', 'मा', 'नजिक', 'पछाडि', 'पहिला', 'पारि',
        'प्रति', 'र', 'संग', 'सहित', 'तल','हरु','तर', 'तिर', 'तर्फ', 'उपर', 'विपरित', 'वरिपरि', 'बिचमा'
    ]
    for suffix in suffixes:
        if word.endswith(suffix):
            return word[:-len(suffix)]
    return word

def remove_stopwords_and_stem(text):
    words = text.split()
    filtered_words = [custom_stem(word) for word in words if word not in custom_stopwords]
    return ' '.join(filtered_words)
