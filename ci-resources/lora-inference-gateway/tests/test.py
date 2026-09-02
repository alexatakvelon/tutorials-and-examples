import sys
import time
import requests

SQL_KEYWORDS = ("select", "from")


def wait_for_response(gateway_ip, model, message, timeout=180):
    url = f"http://{gateway_ip}/v1/chat/completions"
    payload = {"model": model, "messages": [{"role": "user", "content": message}]}
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                body = response.json()
                content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content.strip():
                    return content
            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
        except requests.exceptions.RequestException as e:
            last_error = str(e)
        print(f"Not ready yet ({last_error}), retrying...")
        time.sleep(10)
    raise AssertionError(f"Never got a usable response for model={model!r}. Last error: {last_error}")


def test_base_and_lora_routing(gateway_ip):
    print("=== Querying the base Gemma model ===")
    base_reply = wait_for_response(
        gateway_ip, "google/gemma-3-1b-it", "What is the meaning of life?"
    )
    print(f"Base model reply: {base_reply}")

    print("=== Querying the sql-chat LoRA adapter ===")
    lora_reply = wait_for_response(
        gateway_ip, "sql-chat", "List the three largest cities in Texas by population."
    )
    print(f"sql-chat reply: {lora_reply}")

    lora_reply_lower = lora_reply.lower()
    assert all(k in lora_reply_lower for k in SQL_KEYWORDS), (
        f"Expected the sql-chat LoRA adapter to respond with something SQL-like "
        f"(containing {SQL_KEYWORDS}), but got: {lora_reply}"
    )


gateway_ip = sys.argv[1]
test_base_and_lora_routing(gateway_ip)
print("lora-inference-gateway test passed: base model and sql-chat LoRA adapter both routed and responded correctly.")
