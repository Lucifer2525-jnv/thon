import os
import hashlib

def list_files(root_dir: str, extensions=None):
    if extensions is None:
        extensions = [".pdf", ".docx", ".zip"]
    file_paths = []
    for root, dirs, files in os.walk(root_dir):
        for f in files:
            if any(f.lower().endswith(ext) for ext in extensions):
                file_paths.append(os.path.join(root, f))
    return file_paths

def compute_file_hash(file_path, algo="sha256"):
    h = hashlib.new(algo)
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def detect_duplicates(file_paths):
    hash_map = {}
    duplicates = []
    for path in file_paths:
        h = compute_file_hash(path)
        if h in hash_map:
            duplicates.append((path, hash_map[h]))
        else:
            hash_map[h] = path
    return duplicates