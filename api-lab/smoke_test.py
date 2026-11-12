import requests
import time

SHELF_URL = "https://stillworks.supercapybara.com/api/llm/up"
TIMEOUT = 30

def main():
    print("Fetching hourly-updated public keyless endpoint shelf...")
    shelf_response = requests.get(SHELF_URL, timeout=TIMEOUT)
    print("shelf_http=", shelf_response.status_code)
    shelf_response.raise_for_status()
    shelf = shelf_response.json()
    models = shelf.get("models", [])
    if not models:
        raise SystemExit("No keyless models returned by endpoint shelf.")

    passed = 0
    attempted = 0
    for item in models[:8]:
        base = item.get("openai_base_url", "").rstrip("/")
        model = item.get("model", "")
        if not base or not model:
            continue
        attempted += 1
        print("\nTesting anonymous:", model, "at", base)
        started = time.perf_counter()
        try:
            response = requests.post(
                base + "/chat/completions",
                headers={"Content-Type": "application/json"},
                json={"model": model, "messages": [{"role":"user","content":"Reply with exactly: API TEST OK"}], "max_tokens": 40},
                timeout=TIMEOUT,
            )
            elapsed = round((time.perf_counter()-started)*1000)
            print("http=", response.status_code, "latency_ms=", elapsed)
            if response.ok:
                data = response.json()
                answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if answer:
                    passed += 1
                    print("PASS:", str(answer)[:250])
                else:
                    print("EMPTY RESPONSE:", response.text[:400])
            else:
                print("FAIL:", response.text[:400])
        except Exception as exc:
            print("ERROR:", repr(exc))
        time.sleep(1)

    print("\nSUMMARY: passed", passed, "of", attempted, "anonymous endpoints tested")
    if passed == 0:
        raise SystemExit("No anonymous endpoint returned a successful chat completion.")

if __name__ == "__main__":
    main()
