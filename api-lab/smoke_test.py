import json
import sys
import requests

CATALOG = "https://catalog.endpoints.ai.ovh.net/rest/v1/models_v2"
BASE = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
MODEL = "Qwen3Guard-Gen-0.6B"

def main():
    print("TEST 1: public OVH model catalogue")
    catalog_response = requests.get(CATALOG, timeout=25)
    print("catalog_http=", catalog_response.status_code)
    catalog_response.raise_for_status()
    catalog = catalog_response.json()
    if isinstance(catalog, dict):
        entries = catalog.get("data", catalog.get("models", []))
    else:
        entries = catalog
    match = [m for m in entries if str(m.get("id", m.get("name", ""))).lower() == MODEL.lower()]
    print("model_found=", bool(match))
    if match:
        print("model_available=", match[0].get("available", "not supplied"))

    print("TEST 2: anonymous chat completion (no Authorization header)")
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Classify this harmless text. Reply with a short safety label: Hello, how are you?"}],
        "max_tokens": 80,
        "temperature": 0
    }
    response = requests.post(
        BASE + "/chat/completions",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=45
    )
    print("anonymous_http=", response.status_code)
    print("response_body=", response.text[:1600])
    if not response.ok:
        raise SystemExit("Anonymous inference test failed.")
    data = response.json()
    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not answer:
        raise SystemExit("HTTP success but no model response was returned.")
    print("anonymous_result=PASS")
    print("model_response=", answer[:400])

if __name__ == "__main__":
    main()
