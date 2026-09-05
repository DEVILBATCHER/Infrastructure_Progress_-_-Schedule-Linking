import nltk
nltk.download('punkt_tab')
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
nltk.download('stopwords')
text = "This is a sample text for tokenization."
tokens = word_tokenize(text.lower())
stop_words = set(stopwords.words('english'))
filtered = [word for word in tokens if word not in stop_words]
print(tokens)