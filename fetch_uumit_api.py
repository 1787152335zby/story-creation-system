import requests
import json
from datetime import datetime

API_KEY = "2KuYvkfJq-Wbe_Yd4-GadM9sHjGyVCUTeTEpn-f-axnAFszfw-zYLYBiu7jmuGHw"
USER_ID = "ed7d6739-5b9c-432c-8d26-bc2aecd7912e"
BASE_URL = "https://api.uumit.com/api/v1"

headers = {
    "X-API-Key": API_KEY,
    "X-Platform-User-Id": USER_ID
}

result = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "orders": None,
    "transactions": None,
    "capabilities": None
}

# 调用 orders API
try:
    response = requests.get(f"{BASE_URL}/orders", headers=headers, timeout=10)
    response.raise_for_status()
    result["orders"] = response.json()
    print(f"Orders API 成功: {response.status_code}")
except Exception as e:
    print(f"Orders API 错误: {e}")
    result["orders"] = {"error": str(e)}

print("---SEPARATOR---")

# 调用 transactions API
try:
    response = requests.get(f"{BASE_URL}/transactions", headers=headers, timeout=10)
    response.raise_for_status()
    result["transactions"] = response.json()
    print(f"Transactions API 成功: {response.status_code}")
except Exception as e:
    print(f"Transactions API 错误: {e}")
    result["transactions"] = {"error": str(e)}

print("---SEPARATOR---")

# 调用 capabilities API
try:
    params = {"page": 1, "page_size": 5, "agent_id": USER_ID}
    response = requests.get(f"{BASE_URL}/capabilities", headers=headers, params=params, timeout=10)
    response.raise_for_status()
    result["capabilities"] = response.json()
    print(f"Capabilities API 成功: {response.status_code}")
except Exception as e:
    print(f"Capabilities API 错误: {e}")
    result["capabilities"] = {"error": str(e)}

# 保存结果
with open("uumit_cruise_latest.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("\n结果已保存到 uumit_cruise_latest.json")
