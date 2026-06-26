import os, json
import urllib.request
import urllib.error
import hashlib
import chromadb

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
EMBED_MODEL     = os.environ.get("OLLAMA_MODEL_EMBED", "nomic-embed-text")

# Initialize Local Persistent ChromaDB Client
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

# ──────────────────────────────────────────────────────
#  OLLAMA CORE FUNCTIONS (UNMODIFIED)
# ──────────────────────────────────────────────────────
def ollama_chat(system_prompt: str, messages: list, timeout: int = 180) -> str:
    url = f"{OLLAMA_BASE_URL}/api/chat"
    full = [{"role": "system", "content": system_prompt}] + messages
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": full,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 512,      
            "num_ctx": 32768,        
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        },
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode())
            return body["message"]["content"]
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_BASE_URL}. "
            f"Run `ollama serve` and pull the model with `ollama pull {OLLAMA_MODEL}`. ({e})")
    except (KeyError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Unexpected Ollama response: {e}")

def ollama_health():
    url = f"{OLLAMA_BASE_URL}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            body = json.loads(r.read().decode())
            models = [m["name"] for m in body.get("models", [])]
            return {"ok": True, "model": OLLAMA_MODEL, "models": models}
    except Exception as e:
        return {"ok": False, "model": OLLAMA_MODEL, "error": str(e)}

# ──────────────────────────────────────────────────────
#  RAG & EMBEDDING HELPERS
# ──────────────────────────────────────────────────────
def get_ollama_embedding(text: str) -> list:
    """Generates vector embeddings using Ollama's local embedding API."""
    url = f"{OLLAMA_BASE_URL}/api/embeddings"
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode())
            return body["embedding"]
    except Exception as e:
        raise RuntimeError(f"Failed to generate embedding via Ollama for model '{EMBED_MODEL}': {e}")

def get_codebase_collection_id(files_data: dict) -> str:
    """✅ Hash the actual source code to guarantee recreation on codebase changes."""
    hasher = hashlib.sha256()
    for fname in sorted(files_data.keys()):
        hasher.update(fname.encode('utf-8'))
        src = files_data[fname].get('source', '')
        hasher.update(src.encode('utf-8'))
    return "cb_" + hasher.hexdigest()[:30]

def chunk_codebase(files_data: dict, summary: dict) -> list:
    """✅ Slices source code using exact end_lineno and stores richer Chroma metadata."""
    chunks = []
    lang = summary.get('language', 'unknown')
    
    for fname, fd in files_data.items():
        src = fd.get('source', '')
        lines = src.splitlines()
        if not lines:
            continue

        funcs = sorted(fd.get('functions', {}).values(), key=lambda x: x.get('lineno', 0))
        
        for func in funcs:
            start_idx = max(0, func.get('lineno', 1) - 1)
            # Use strict end_lineno, fallback to loc math if the AST skipped it
            end_idx = func.get('end_lineno', start_idx + func.get('loc', 1))
                
            chunk_text = "\n".join(lines[start_idx:end_idx])
            if not chunk_text.strip():
                continue

            chunks.append({
                "text": f"File: {fname}\nFunction: {func['name']}\nCode:\n{chunk_text}",
                "metadata": {
                    "filename": fname,
                    "function_name": func['name'],
                    "class_name": func.get('class_name') or "None",
                    "start_line": start_idx + 1,
                    "end_line": end_idx,
                    "complexity": func.get('complexity', 1),
                    "has_db_io": str(func.get('has_db_io', False)),
                    "language": lang
                }
            })
            
        # Fallback for structural files without defined functions
        if not funcs and src.strip():
            page_size = 100
            for i in range(0, len(lines), page_size):
                chunk_text = "\n".join(lines[i:i+page_size])
                chunks.append({
                    "text": f"File: {fname}\nCode:\n{chunk_text}",
                    "metadata": {
                        "filename": fname,
                        "function_name": "None",
                        "class_name": "None",
                        "start_line": i + 1,
                        "end_line": min(len(lines), i + page_size),
                        "complexity": 0,
                        "has_db_io": "False",
                        "language": lang
                    }
                })
    return chunks

def populate_vector_db_if_needed(files_data: dict, summary: dict):
    """Ensures the project codebase is split and stored in ChromaDB exactly once."""
    coll_id = get_codebase_collection_id(files_data)
    try:
        coll = chroma_client.get_collection(name=coll_id)
        if coll.count() > 0:
            return coll
    except Exception:
        pass

    coll = chroma_client.get_or_create_collection(name=coll_id)
    chunks = chunk_codebase(files_data, summary)
    
    if not chunks:
        return coll

    ids, embeddings, metadatas, documents = [], [], [], []
    for idx, chunk in enumerate(chunks):
        ids.append(f"chunk_{idx}")
        embeddings.append(get_ollama_embedding(chunk["text"]))
        metadatas.append(chunk["metadata"])
        documents.append(chunk["text"])

    coll.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
    return coll

# ──────────────────────────────────────────────────────
#  CONTEXT BUILDING PIPELINE (TRUE GRAPHRAG)
# ──────────────────────────────────────────────────────
def build_compact_context(summary: dict, files_data: dict, user_msg: str) -> str:
    lang = summary.get('language', 'unknown')
    lines = [
        f"CODEBASE ARCHITECTURE (100% ACCURATE DATA):",
        f"Language: {lang}",
    ]

    # 1. Build Call Graph String & Bidirectional Graph Lookup
    all_funcs = []
    func_lookup = {}
    incoming_graph = {}
    
    for fname, fd in (files_data or {}).items():
        for fk, fn_data in fd.get('functions', {}).items():
            entry = fn_data['name']
            if fn_data.get('class_name'):
                entry = f"{fn_data['class_name']}.{fn_data['name']}"
                
            func_id = f"{fname}::{fn_data['name']}"
            func_lookup[func_id] = (fname, fn_data)
            
            calls = fn_data.get('calls', [])
            if calls:
                entry += f" calls ➔ [{', '.join(calls)}]"
                # Map incoming edges for reverse traversal
                for call in calls:
                    if call not in incoming_graph:
                        incoming_graph[call] = set()
                    incoming_graph[call].add(func_id)
            all_funcs.append(entry)

    if all_funcs:
        lines.append("EXTRACTED CALL GRAPH:")
        lines.append('\n'.join(all_funcs))

    lines.append("\n--- RELEVANT RAW SOURCE CODE CHUNKS (SEMANTIC RETRIEVAL) ---")

    # 2. Query Semantic DB & 3. Execute Bidirectional Graph Expansion
    if files_data:
        try:
            coll = populate_vector_db_if_needed(files_data, summary)
            query_vector = get_ollama_embedding(user_msg)
            results = coll.query(query_embeddings=[query_vector], n_results=5)
            
            retrieved_functions = set()
            if results and results['documents'] and results['documents'][0]:
                for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                    lines.append(f"\n[Semantic Chunk - Lines {meta['start_line']}:{meta['end_line']}]\n{doc}\n---")
                    if meta.get('function_name') and meta['function_name'] != "None":
                        retrieved_functions.add((meta['filename'], meta['function_name']))

            # ✅ True GraphRAG: Expand context using callers & callees with exact line bounds
            added_neighbors = set()
            neighbor_count = 0
            max_neighbors = 4 # Hard token ceiling
            
            for r_fname, r_func_name in retrieved_functions:
                if neighbor_count >= max_neighbors: 
                    break
                
                r_fd = files_data.get(r_fname, {})
                r_fn_data = next((f for f in r_fd.get('functions', {}).values() if f['name'] == r_func_name), None)
                if not r_fn_data: 
                    continue
                
                # Expand Outgoing (Callees)
                for call in r_fn_data.get('calls', []):
                    for target_id, (t_fname, t_fn_data) in func_lookup.items():
                        if t_fn_data['name'] == call and target_id not in added_neighbors:
                            t_start = max(0, t_fn_data.get('lineno', 1) - 1)
                            t_end = t_fn_data.get('end_lineno', t_start + t_fn_data.get('loc', 1))
                            t_src = "\n".join(files_data[t_fname].get('source', '').splitlines()[t_start:t_end])
                            
                            lines.append(f"\n[Graph Expansion (Callee) - {r_func_name}() calls {t_fn_data['name']}()]\nCode:\n{t_src}\n---")
                            added_neighbors.add(target_id)
                            neighbor_count += 1
                            break
                
                # Expand Incoming (Callers)
                callers = incoming_graph.get(r_func_name, set())
                for caller_id in callers:
                    if caller_id not in added_neighbors and neighbor_count < max_neighbors:
                        c_fname, c_fn_data = func_lookup[caller_id]
                        c_start = max(0, c_fn_data.get('lineno', 1) - 1)
                        c_end = c_fn_data.get('end_lineno', c_start + c_fn_data.get('loc', 1))
                        c_src = "\n".join(files_data[c_fname].get('source', '').splitlines()[c_start:c_end])
                        
                        lines.append(f"\n[Graph Expansion (Caller) - {c_fn_data['name']}() calls {r_func_name}()]\nCode:\n{c_src}\n---")
                        added_neighbors.add(caller_id)
                        neighbor_count += 1

        except Exception as e:
            lines.append(f"(Semantic retrieval error: {e}. Falling back to structural details.)")
    else:
        lines.append("(No files available to search.)")

    return '\n'.join(lines)