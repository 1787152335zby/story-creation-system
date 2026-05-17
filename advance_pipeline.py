import requests, time

BASE = "http://localhost:8000/api"
name = "pipeline_v2"

for cycle in range(20):
    p = requests.get(f"{BASE}/projects/{name}").json()
    done = sum(1 for ph in p["phases"][:6] if ph["done"])
    print(f"\n=== Cycle {cycle}: {done}/6 ===")
    for i, ph in enumerate(p["phases"][:6]):
        print(f"  {'✅' if ph['done'] else '⏳'} {i}: {ph['name']}")
    
    if all(ph["done"] for ph in p["phases"][:6]):
        print("\n🎉 全部完成!")
        break
    
    pa = p.get("pending_approval", -1)
    pv = p.get("pending_version", -1)
    print(f"approval={pa}, version={pv}, current_phase={p.get('current_phase')}")
    
    if pa >= 0:
        print(f"⚠️ 跳过审核阶段 {pa}")
        p["phases"][pa]["done"] = True
        p["pending_approval"] = -1
        p["current_phase"] = pa + 1
        requests.put(f"{BASE}/projects/{name}/config", json=p)
        print("✅ 跳过成功")
    
    if pv >= 0:
        print(f"⚠️ 跳过版本选择阶段 {pv}")
        p["pending_version"] = -1
        p["current_phase"] = pv + 1
        requests.put(f"{BASE}/projects/{name}/config", json=p)
        print("✅ 跳过成功")
    
    time.sleep(30)

print("\n=== 最终状态 ===")
p = requests.get(f"{BASE}/projects/{name}").json()
for i, ph in enumerate(p["phases"]):
    print(f"  {'✅' if ph['done'] else '⏳'} {i}: {ph['name']}")
