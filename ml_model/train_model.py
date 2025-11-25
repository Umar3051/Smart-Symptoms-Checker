import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import joblib
import os

# Paths
CSV_FILE = os.path.join("ml_model", "diseases.csv")
MODEL_FILE = os.path.join("ml_model", "disease_model.pkl")
ENCODER_FILE = os.path.join("ml_model", "label_encoder.pkl")
PICKLE_FILE = os.path.join("ml_model", "diseases.pkl")

# Load CSV
try:
    df_csv = pd.read_csv(CSV_FILE)
except FileNotFoundError:
    raise FileNotFoundError(f"{CSV_FILE} not found. Please create it with disease data.")

# Build list of all unique symptoms
all_symptoms = set()
for idx, row in df_csv.iterrows():
    for col in df_csv.columns:
        if col.lower().startswith("symptom"):
            val = row[col]
            if pd.notna(val):
                all_symptoms.add(str(val).lower().strip())
all_symptoms = sorted(list(all_symptoms))

# Prepare feature matrix
data = []
for _, row in df_csv.iterrows():
    row_dict = {symptom: 0 for symptom in all_symptoms}
    for col in df_csv.columns:
        if col.lower().startswith("symptom"):
            val = row[col]
            if pd.notna(val):
                row_dict[str(val).lower().strip()] = 1
    row_dict['disease'] = row['disease']
    data.append(row_dict)

df = pd.DataFrame(data)
X = df.drop("disease", axis=1)
y = LabelEncoder().fit_transform(df['disease'])

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X_train, y_train)

# Accuracy
accuracy = model.score(X_test, y_test)
print(f"Model trained! Test accuracy: {accuracy}")

# Save model and label encoder
le = LabelEncoder()
le.fit(df['disease'])
joblib.dump(model, MODEL_FILE)
joblib.dump(le, ENCODER_FILE)
print(f"Saved model to {MODEL_FILE} and encoder to {ENCODER_FILE}")

# Save diseases data (pickle) for fast lookup in routes/items.py
diseases_records = []
for _, row in df_csv.iterrows():
    symptoms_list = []
    for col in df_csv.columns:
        if col.lower().startswith("symptom"):
            val = row[col]
            if pd.notna(val):
                symptoms_list.append(str(val).lower().strip())
    diseases_records.append({"disease": str(row['disease']).strip(), "symptoms": symptoms_list})

joblib.dump(diseases_records, PICKLE_FILE)
print(f"Diseases data saved to {PICKLE_FILE}")