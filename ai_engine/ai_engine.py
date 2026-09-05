import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
text = "This is a sample text for tokenization."
tokens = word_tokenize(text.lower())
stop_words = set(stopwords.words('english'))
filtered = [word for word in tokens if word not in stop_words]
lemmatized = [lemmatizer.lemmatize(word) for word in filtered]
print(lemmatized)