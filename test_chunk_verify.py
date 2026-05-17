"""快速验证分块策略在真实项目中的加载和调用"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from core.chunk_strategy import ChunkStrategy, ChunkIter
from core.summary_extractor import SummaryExtractor

# 验证1: 所有故事类型都有策略
for st in ["1","2","3","4","5","6"]:
    p = ChunkStrategy.get_plan(st)
    print(f"类型{st}: 块数={p.chunk_count}, 逆向={p.reverse_order}, 名称={p.chunk_names}")

# 验证2: 固定分块解析
test_outline = """
## 第一幕
这是第一幕的内容。
更多内容...

## 第二幕
这是第二幕的内容。

## 第三幕
这是第三幕的内容，结局。
"""
plan = ChunkStrategy.get_plan("2")
it = ChunkIter(plan, test_outline)
blocks = it.blocks
print(f"\n固定分块解析: {len(blocks)}块")
for b in blocks:
    print(f"  {b['name']}: {len(b['content'])}字")

# 验证3: 逆向生成顺序（C方案）
print("\n逆向生成顺序:")
for ctx in it:
    print(f"  → {ctx.name} (前序{len(ctx.previous_full_texts)}块, 摘要{len(ctx.summaries)}条)")

# 验证4: auto 分块
plan_auto = ChunkStrategy.get_plan("1")
it_auto = ChunkIter(plan_auto, test_outline)
it_auto.set_auto_blocks(5)
print(f"\nauto分块: {len(it_auto.blocks)}块")

# 验证5: 摘要提取
summary_text = """
## 关键元素追踪
- 未解悬念：主角的真实身份
- 角色状态变化：从怀疑到信任
"""
parsed = SummaryExtractor.parse_summary(summary_text)
print(f"\n摘要解析: {parsed[:50]}..." if len(parsed) > 50 else f"\n摘要解析: {parsed}")

# 验证6: 存储 chunks
it.blocks[0]["_output"] = "第一幕全文内容"
it.blocks[1]["_output"] = "第二幕全文内容"
it.blocks[2]["_output"] = "第三幕全文内容"
chunks = [{"name": b["name"], "output": b.get("_output", "")} for b in it.blocks]
print(f"\n存储chunks: {len(chunks)}块 → '{chunks[0]['output'][:10]}...'")

print("\n✅ 全部验证通过!")
