$env:Path = "C:\Git\bin;$env:Path"
cd "E:\AI\Trae CN\book\故事创作系统"

# 把 .node 目录也加到 .gitignore
Add-Content .gitignore "`n.node/"

# 取消暂存不需要的文件
git reset HEAD ".node/" 2>$null
git reset HEAD "generated/" 2>$null
git reset HEAD "_tmp.json" 2>$null
git reset HEAD "test_chunk_verify.py" 2>$null
git reset HEAD "*.bak" 2>$null
git reset HEAD "*.bak2" 2>$null
git reset HEAD "orchestrator_router.txt" 2>$null
git reset HEAD "pipeline_direct_log.txt" 2>$null
git reset HEAD "需求文档_API_Key前端配置.md" 2>$null
git reset HEAD "project_config.json" 2>$null
git reset HEAD "templates/" 2>$null

# 统计最终提交的大小
$total = 0
git diff --cached --name-only | ForEach-Object {
    if (Test-Path $_ -PathType Leaf) { $total += (Get-Item $_).Length }
}
Write-Output "提交大小: $([math]::Round($total/1MB,2)) MB"

# 提交
git commit -m "初始化：多智能体故事创作系统"

Write-Output "`n✅ 提交完成"

# 添加远程仓库
git remote add origin https://github.com/1787152335zby/story-creation-system.git
Write-Output "✅ 远程仓库已配置"

Write-Output "`n准备推送到 GitHub..."
Write-Output "（需要输入你的 GitHub 密码或 Token）"
