from fastapi import APIRouter, HTTPException, Depends
import pandas as pd
import joblib
import os
import random
from rapidfuzz import process
from auth.auth_handler import get_current_user

router = APIRouter()

PKL_DATA_PATH = os.path.join("ml_model", "diseases.pkl")
CSV_DATA_PATH = os.path.join("ml_model", "diseases.csv")

_diseases_cache = None

def load_diseases_data():
    global _diseases_cache
    if _diseases_cache is not None:
        return _diseases_cache
    if os.path.exists(PKL_DATA_PATH):
        try:
            _diseases_cache = joblib.load(PKL_DATA_PATH)
            normalized = []
            for rec in _diseases_cache:
                disease = rec.get("disease") if isinstance(rec, dict) else None
                symptoms = rec.get("symptoms") if isinstance(rec, dict) else None
                if disease and isinstance(symptoms, (list, tuple)):
                    normalized.append({
                        "disease": str(disease).strip(),
                        "symptoms": [str(s).lower().strip() for s in symptoms if s]
                    })
            _diseases_cache = normalized
            return _diseases_cache
        except Exception as e:
            raise RuntimeError(f"Failed to load PKL disease data: {e}")
    if os.path.exists(CSV_DATA_PATH):
        try:
            df = pd.read_csv(CSV_DATA_PATH)
            records = []
            symptom_cols = [c for c in df.columns if c.lower().startswith("symptom")]
            for _, row in df.iterrows():
                disease = row.get("disease", "")
                symptoms = []
                for col in symptom_cols:
                    val = row.get(col)
                    if pd.isna(val):
                        continue
                    s = str(val).lower().strip()
                    if s:
                        symptoms.append(s)
                records.append({"disease": str(disease).strip(), "symptoms": symptoms})
            _diseases_cache = records
            return _diseases_cache
        except Exception as e:
            raise RuntimeError(f"Failed to load CSV disease data: {e}")
    raise RuntimeError(
        f"No disease data found. Expected '{PKL_DATA_PATH}' or '{CSV_DATA_PATH}' in ml_model folder."
    )

@router.post("/predict_disease")
def predict_disease(input: dict, user=Depends(get_current_user)):
    symptoms = input.get("symptoms") if isinstance(input, dict) else None
    if not isinstance(symptoms, (list, tuple)):
        raise HTTPException(status_code=400, detail="Invalid payload. Expected {'symptoms': [..]}")
    symptoms_input = [s.lower().strip() for s in symptoms if s.strip() != ""]
    if len(symptoms_input) < 4 or len(symptoms_input) > 6:
        raise HTTPException(status_code=400, detail="Please provide 4 to 6 symptoms")
    try:
        diseases = load_diseases_data()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    all_known_symptoms = set()
    for rec in diseases:
        for s in rec.get("symptoms", []):
            all_known_symptoms.add(s.lower().strip())
    valid_symptoms = []
    invalid_symptoms = []
    suggestions = {}
    for s in symptoms_input:
        if s in all_known_symptoms:
            valid_symptoms.append(s)
        else:
            invalid_symptoms.append(s)
            best_match = process.extractOne(s, list(all_known_symptoms), score_cutoff=70)
            if best_match:
                suggestions[s] = best_match[0]
    if len(valid_symptoms) < 4:
        detail_msg = f"Too few valid symptoms. Invalid symptoms: {', '.join(invalid_symptoms)}"
        if suggestions:
            suggestion_msg = "; ".join([f"{k} → {v}" for k, v in suggestions.items()])
            detail_msg += f". Did you mean: {suggestion_msg}?"
        raise HTTPException(status_code=400, detail=detail_msg)
    matched_diseases = []
    for rec in diseases:
        item_symptoms = [s.lower() for s in rec.get("symptoms", [])]
        match_count = sum(1 for s in valid_symptoms if s in item_symptoms)
        if match_count >= 2:
            percent = int((match_count / len(valid_symptoms)) * 100)
            if percent > 50:
                percent = random.randint(max(50, percent-10), min(100, percent+10))
            matched_diseases.append({
                "disease": rec.get("disease"),
                "match_percent": percent
            })
    if not matched_diseases:
        detail_msg = f"No diseases matched your symptoms. Invalid symptoms: {', '.join(invalid_symptoms)}"
        if suggestions:
            suggestion_msg = "; ".join([f"{k} → {v}" for k, v in suggestions.items()])
            detail_msg += f". Did you mean: {suggestion_msg}?"
        raise HTTPException(status_code=404, detail=detail_msg)
    random.shuffle(matched_diseases)
    matched_diseases = sorted(matched_diseases, key=lambda x: x["match_percent"], reverse=True)[:5]
    return {
        "diseases": matched_diseases,
        "valid_symptoms": valid_symptoms,
        "invalid_symptoms": invalid_symptoms,
        "suggestions": suggestions
    }