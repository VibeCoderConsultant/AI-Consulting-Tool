import time, uuid, requests
from bot.config import AUTH_KEY, VERIFY_CERT_PATH, logger

_token = {"value": None, "ts": 0, "ttl": 36000}

def get_access_token() -> str:
    now = time.time()
    if _token["value"] and now - _token["ts"] < _token["ttl"]:
        return _token["value"]
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {AUTH_KEY}",
    }
    resp = requests.post(url, headers=headers, data="scope=GIGACHAT_API_PERS", verify=VERIFY_CERT_PATH)
    resp.raise_for_status()
    token = resp.json()["access_token"]
    _token.update({"value": token, "ts": now})
    return token

def call_gigachat(messages: list, temperature: float, top_p: float = 0.9, max_tokens: int = 120) -> str:
    token = get_access_token()
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"model":"GigaChat", "messages":messages, "temperature":temperature, "top_p":top_p, "max_tokens":max_tokens}
    resp = requests.post(url, headers=headers, json=payload, verify=VERIFY_CERT_PATH)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()