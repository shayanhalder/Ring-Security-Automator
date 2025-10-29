import cv2
import os
import numpy as np
from insightface.app import FaceAnalysis

# Initialize ArcFace embedding model
# app = FaceAnalysis(name="arcface_r100_v1", providers=['CPUExecutionProvider'])
app = FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

known_faces_dir = "known_faces"
encodings = {}
for person_name in os.listdir(known_faces_dir):
    person_dir = os.path.join(known_faces_dir, person_name)
    if not os.path.isdir(person_dir):
        continue

    embeddings = []
    for img_name in os.listdir(person_dir):
        img_path = os.path.join(person_dir, img_name)
        img = cv2.imread(img_path)
        if img is None:
            continue

        faces = app.get(img)
        if len(faces) == 0:
            print(f"[WARN] No face found in {img_path}")
            continue

        # Take the first face’s embedding
        emb = faces[0].embedding
        embeddings.append(emb)

    if len(embeddings) > 0:
        encodings[person_name] = np.mean(embeddings, axis=0)
        print(f"[INFO] Encoded {person_name} with {len(embeddings)} images")

# Save encodings
np.save("face_encodings.npy", encodings)
print("[INFO] Saved embeddings to face_encodings.npy")
