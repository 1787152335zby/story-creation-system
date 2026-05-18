param(
    [Parameter(Mandatory=$true)]
    [string]$RepoUrl
)

Write-Host "=== 准备推送到 GitHub ===" -ForegroundColor Cyan
Write-Host "仓库地址: $RepoUrl" -ForegroundColor Yellow
Write-Host ""

# 1. 初始化 Git
if (-not (Test-Path ".git")) {
    git init
    Write-Host "✅ Git 初始化完成" -ForegroundColor Green
} else {
    Write-Host "ℹ️ Git 已初始化" -ForegroundColor Yellow
}

# 2. 设置远程仓库
$remote = git remote get-url origin 2>$null
if (-not $remote) {
    git remote add origin $RepoUrl
    Write-Host "✅ 远程仓库已添加: $RepoUrl" -ForegroundColor Green
} else {
    Write-Host "ℹ️ 远程仓库已存在: $remote" -ForegroundColor Yellow
}

# 3. 添加所有文件
git add .

# 4. 检查 .gitignore 排除的内容
Write-Host ""
Write-Host "=== .gitignore 已排除以下内容 ===" -ForegroundColor Cyan
Get-Content .gitignore | Where-Object { $_ -ne '' -and $_ -notmatch '^#' }

# 5. 统计提交大小
$total = 0
git diff --cached --name-only | ForEach-Object {
    if (Test-Path $_ -PathType Leaf) { $total += (Get-Item $_).Length }
}
Write-Host ""
Write-Host "提交大小: $([math]::Round($total/1MB,2)) MB" -ForegroundColor Yellow

# 6. 提交
Write-Host ""
Write-Host "=== 提交代码 ===" -ForegroundColor Cyan
git commit -m "场景多角度：鸟瞰图+参考生正视图，版本管理，确认图片引用"

# 7. 推送到 GitHub
Write-Host ""
Write-Host "=== 推送到 GitHub ===" -ForegroundColor Cyan
git push -u origin main

Write-Host ""
Write-Host "✅ 完成！" -ForegroundColor Green
