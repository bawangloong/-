# 需要先安装 PyInstaller：pip install pyinstaller
# 用法：powershell -ExecutionPolicy Bypass -File build/build_exe.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$pyinstaller = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pyinstaller) {
    Write-Host '未找到 pyinstaller，请先执行：pip install pyinstaller' -ForegroundColor Yellow
    exit 1
}

Write-Host '== 清理旧的 dist/build 产物'
if (Test-Path "$root\dist\车牌识别系统") { Remove-Item "$root\dist\车牌识别系统" -Recurse -Force }
if (Test-Path "$root\build\车牌识别系统") { Remove-Item "$root\build\车牌识别系统" -Recurse -Force }

Write-Host '== 开始打包'
& pyinstaller "$root\build\plate_app.spec" --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller 打包失败' }

Write-Host '== 复制说明文件'
Copy-Item "$root\README.md", "$root\requirements.txt" "$root\dist\车牌识别系统\" -ErrorAction SilentlyContinue
Copy-Item "$root\docs" "$root\dist\车牌识别系统\docs" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host '== 完成：dist\车牌识别系统\车牌识别系统.exe'
