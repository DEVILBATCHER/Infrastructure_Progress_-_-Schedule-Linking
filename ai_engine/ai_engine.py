import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
vectorizer = TfidfVectorizer()

documents = [
    "12 inch spool erection completed at Unit 3",
    "Install 12-inch carbon steel pipeline"
]
tfidf_matrix = vectorizer.fit_transform(documents)
cosine_sim = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])
print(vectorizer.get_feature_names_out())
print(tfidf_matrix.toarray())
print("Cosine Similarity:", cosine_sim[0][0])