import nltk
nltk.download('punkt')
from nltk.tokenize import word_tokenize
text = "This is a sample text for tokenization."
tokens = word_tokenize(text.lower())
print(tokens)