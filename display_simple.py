
import json

# 读取文件
with open('uumit_cruise_last.json', 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

print("="*60)
print("UUMit 巡航检查结果")
print("="*60)
print(f"检查时间: {data.get('timestamp')}")
print()

capabilities = data.get('capabilities', {})
items = capabilities.get('items', [])
count = capabilities.get('count', 0)

if count > 0:
    print(f"发现 {count} 个新能力：")
    print("-"*60)
    
    # 分类统计
    categories = {}
    for item in items:
        cat = item.get('category', '未分类')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    # 显示每个分类
    for cat, cat_items in categories.items():
        print(f"\n{cat} ({len(cat_items)}个)")
        for i, item in enumerate(cat_items, 1):
            print(f"\n{i}. {item.get('title')}")
            print(f"   价格: {item.get('price_ut')} UT")
            print(f"   类型: {item.get('capability_type')}")
            print(f"   可用: {'是' if item.get('available') else '否'}")

print("\n" + "="*60)
print("检查完成！")
print("="*60)
