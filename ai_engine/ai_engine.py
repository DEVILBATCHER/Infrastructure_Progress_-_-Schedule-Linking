from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np  
model = SentenceTransformer('all-MiniLM-L6-v2')
schedule = [
    "Install 12-inch carbon steel pipeline",
    "Replace 6-inch gate valve at Unit 2",
    "Erect structural steel column at Bay 4"
]

report_line = "12 inch spool erection completed at Unit 3"
report_embedding = model.encode(report_line)
schedule_embeddings = model.encode(schedule)

score = cosine_similarity([report_embedding], schedule_embeddings)
results = list(zip(schedule, score[0]))
results.sort(key=lambda x: x[1], reverse=True)

top_k = 2
for activity, score in results[:top_k]:
    print(f"{score:.3f}  -  {activity}")