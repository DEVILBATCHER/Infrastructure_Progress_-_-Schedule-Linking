from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
report_line = "12 inch spool erection completed at Unit 3"
schedule_desc = "Install 12-inch carbon steel pipeline"
report_embedding = model.encode(report_line)
schedule_embedding = model.encode(schedule_desc)
from sklearn.metrics.pairwise import cosine_similarity
score = cosine_similarity([report_embedding], [schedule_embedding])
print("Cosine Similarity:", score[0][0])