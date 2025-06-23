from app.utils.file_discovery import list_files, detect_duplicates, compute_file_hash
from app.utils.extractors import extract_text
from app.agents.classifier_agent import classify_document
from app.agents.policy_agent import match_policy

def process_file_pipeline(directory: str):
    files = list_files(directory)
    duplicates = detect_duplicates(files)
    results = []

    for file_path in files:
        content = extract_text(file_path)
        file_hash = compute_file_hash(file_path)

        classification = classify_document(content)
        policy_action = match_policy(content, {"file_path": file_path})

        results.append({
            "file": file_path,
            "hash": file_hash,
            "is_duplicate": any(file_path in dup for dup in duplicates),
            "classification": classification,
            "policy_action": policy_action
        })

    return results