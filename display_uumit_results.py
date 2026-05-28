
import json
import sys
from datetime import datetime

# 读取文件路径
file_path = 'uumit_cruise_last.json'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("="*60)
    print("🚀 UUMit 巡航检查结果")
    print("="*60)
    print(f"检查时间: {data.get('timestamp')}")
    print()
    
    # 显示新能力
    capabilities = data.get('capabilities', {})
    items = capabilities.get('items', [])
    count = capabilities.get('count', 0)
    
    if count > 0:
        print(f"🎯 发现 {count} 个新能力：")
        print("-"*60)
        
        # 统计分类
        categories = {}
        for item in items:
            cat = item.get('category', '未分类')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        # 按分类显示
        for cat, cat_items in categories.items():
            print(f"\n📂 {cat} ({len(cat_items)}个)")
            for item in cat_items:
                print(f"\n   ├─ 标题: {item.get('title')}")
                print(f"   │  ID: {item.get('id')[:20]}...")
                print(f"   │  价格: {item.get('price_ut')} UT")
                print(f"   │  类型: {item.get('capability_type')}")
                print(f"   │  质量分数: {item.get('quality_score')}")
                desc = item.get('description', '')
                if desc:
                    if len(desc) &gt; 50:
                        desc = desc[:47] + '...'
                    print(f"   │  描述: {desc}")
                print(f"   └─ 可用: {'是' if item.get('available') else '否'}")
    
    print("\n" + "="*60)
    print("检查完成！")
    print("="*60)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

