import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
vectorizer = TfidfVectorizer()
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
documents = [
    "12 inch spool erection completed at Unit 3",
    "Install 12-inch carbon steel pipeline"
]
tfidf_matrix = vectorizer.fit_transform(documents)
print(vectorizer.get_feature_names_out())
print(tfidf_matrix.toarray())
def preprocess_tfidf(text):
    tokens = word_tokenize(text.lower())
    stop_words = set(stopwords.words('english'))
    filtered = [word for word in tokens if word not in stop_words]
    lemmatized = [lemmatizer.lemmatize(word) for word in filtered]
    return lemmatized
text = "This is a sample text for tokenization."
lemmatized = preprocess_tfidf(text)
print(lemmatized)