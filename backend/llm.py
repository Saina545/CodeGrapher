import os, json
import urllib.request
import urllib.error

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")

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

def build_compact_context(summary: dict, files_data: dict, user_msg: str) -> str:
    lang  = summary.get('language', 'unknown')
    lines = [
        f"CODEBASE ARCHITECTURE (100% ACCURATE DATA):",
        f"Language: {lang}",
    ]

    all_funcs = []
    relevant_files = set()
    user_msg_lower = user_msg.lower()
    
    for fname, fd in (files_data or {}).items():
        is_relevant = False
        if fname.lower() in user_msg_lower:
            is_relevant = True
            
        for fk, fn_data in fd.get('functions', {}).items():
            entry = fn_data['name']
            if fn_data.get('class_name'):
                entry = f"{fn_data['class_name']}.{fn_data['name']}"
            calls = fn_data.get('calls', [])
            if calls:
                entry += f" calls ➔ [{', '.join(calls)}]"
            all_funcs.append(entry)
            
            if fn_data['name'].lower() in user_msg_lower:
                is_relevant = True
                
        if is_relevant:
            relevant_files.add(fname)

    if all_funcs:
        lines.append("EXTRACTED CALL GRAPH:")
        lines.append('\n'.join(all_funcs))

    lines.append("\n--- RELEVANT RAW SOURCE CODE ---")
    found_code = False
    for fname in relevant_files:
        src = files_data.get(fname, {}).get('source', '')
        if src:
            lines.append(f"\nFile: {fname}\n---\n{src[:15000]}\n---")
            found_code = True
            
    if not found_code:
        lines.append("(No specific file matched the query. Use the CALL GRAPH above to answer.)")

    return '\n'.join(lines)