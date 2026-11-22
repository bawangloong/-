# 构建“免安装 Python”绿色发行包（本机无 PyInstaller 时的可运行 exe 方案）
# 用法：powershell -ExecutionPolicy Bypass -File build/make_portable.ps1
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$stage = Join-Path $root 'dist\车牌识别系统'
$py = 'C:\Program Files\Python313'
$site = Join-Path $env:APPDATA 'Python\Python313\site-packages'

Write-Host "== 清理 $stage"
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force $stage, "$stage\runtime", "$stage\runtime\Lib", "$stage\runtime\DLLs" | Out-Null

Write-Host '== 复制 Python 运行时'
Copy-Item "$py\python.exe", "$py\pythonw.exe", "$py\python3.dll", "$py\python313.dll", "$py\vcruntime140.dll", "$py\vcruntime140_1.dll" "$stage\runtime\"
robocopy "$py\DLLs" "$stage\runtime\DLLs" /E /NFL /NDL /NJH /NJS /NP | Out-Null
robocopy "$py\tcl" "$stage\runtime\tcl" /E /NFL /NDL /NJH /NJS /NP | Out-Null
robocopy "$py\Lib" "$stage\runtime\Lib" /E /XD test site-packages idlelib ensurepip lib2to3 turtledemo pydoc_data __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -gt 7) { throw "复制 Lib 失败：$LASTEXITCODE" }

Write-Host '== 复制第三方库'
$packages = @('cv2', 'numpy', 'numpy.libs', 'PIL', 'numpy-2.3.5.dist-info',
              'opencv_contrib_python-5.0.0.93.dist-info', 'pillow-12.0.0.dist-info')
foreach ($pkg in $packages) {
    $src = Join-Path $site $pkg
    if (Test-Path $src) {
        robocopy $src "$stage\runtime\Lib\site-packages\$pkg" /E /NFL /NDL /NJH /NJS /NP | Out-Null
    }
}
# 图片识别不需要视频编解码器，去掉可减小约 30 MB；如报 videoio 相关错误再放回。
$ffmpeg = "$stage\runtime\Lib\site-packages\cv2\opencv_videoio_ffmpeg500_64.dll"
if (Test-Path $ffmpeg) { Remove-Item $ffmpeg -Force }

Write-Host '== 复制项目文件'
foreach ($item in 'app', 'vendor', 'samples', 'docs') {
    robocopy (Join-Path $root $item) (Join-Path $stage $item) /E /XD __pycache__ _tmp /NFL /NDL /NJH /NJS /NP | Out-Null
}
Copy-Item "$root\README.md" $stage -ErrorAction SilentlyContinue
Copy-Item "$root\requirements.txt" $stage -ErrorAction SilentlyContinue
Copy-Item "$root\app_main.py" $stage

Write-Host '== 编译启动器'
$csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
& $csc /nologo /target:winexe /optimize+ /out:"$stage\车牌识别系统.exe" "$root\build\Launcher.cs"
if ($LASTEXITCODE -ne 0) { throw '启动器编译失败' }

Write-Host "== 完成：$stage"
$size = (Get-ChildItem $stage -Recurse -File | Measure-Object Length -Sum).Sum
Write-Host ("   大小 {0:N1} MB" -f ($size / 1MB))
