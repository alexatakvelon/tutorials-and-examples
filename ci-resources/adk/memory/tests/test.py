import sys
import json
import requests

APP_NAME = "agent_with_memory"


def create_session(base_url, user_id):
    url = f'{base_url}/apps/{APP_NAME}/users/{user_id}/sessions'
    headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers)
    response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
    session_id = response.json()["id"]
    assert session_id is not None, "The Session ID is None."
    return session_id


def send_message(base_url, user_id, session_id, text):
    url = f'{base_url}/run_sse'
    headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
    data = {
        "appName": APP_NAME,
        "userId": user_id,
        "sessionId": str(session_id),
        "newMessage": {
            "parts": [{"text": text}],
            "role": "user",
        },
        "streaming": False,
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
    print("Status Code:", response.status_code)

    output = response.text.split("data: ")[1:]
    events = [json.loads(chunk) for chunk in output]

    # Collect every text part across every SSE event. Tool-call/tool-response
    # events don't carry a "text" part, only the model's final reply does, so
    # concatenating whatever text parts exist gives us the agent's reply
    # regardless of how many tool round-trips happened first.
    texts = []
    for event in events:
        for part in event.get("content", {}).get("parts", []):
            if "text" in part:
                texts.append(part["text"])
    return " ".join(texts)


def test_memory_persists_across_sessions(base_url):
    user_id = "ci-test-user"
    fact = "my favorite programming language is Rust"

    # Turn 1: teach the agent a fact and ask it to remember it, in a fresh session.
    session_1 = create_session(base_url, user_id)
    reply_1 = send_message(
        base_url, user_id, session_1,
        f"Please remember this fact about me: {fact}.",
    )
    print(f"Turn 1 response: {reply_1}")
    assert reply_1, "Agent gave an empty response while being taught a fact."

    # Turn 2: open a brand-new session and ask the agent to recall the fact.
    # This only succeeds if search_memory actually retrieved it from the
    # mem0/pgvector-backed store rather than from in-session chat context -
    # which is the entire point of this tutorial.
    session_2 = create_session(base_url, user_id)
    reply_2 = send_message(
        base_url, user_id, session_2,
        "What is my favorite programming language? Answer in one word.",
    )
    print(f"Turn 2 response: {reply_2}")
    assert "rust" in reply_2.lower(), (
        f"Expected the agent to recall 'Rust' from persistent memory in a new "
        f"session, but got: {reply_2}"
    )


base_url = sys.argv[1]
test_memory_persists_across_sessions(base_url)
print("adk/memory test passed: fact recalled from persistent memory across sessions.")
