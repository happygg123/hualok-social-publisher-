$ErrorActionPreference = 'Continue'
$target = Get-Process | Where-Object { $_.ProcessName -eq 'chrome' -and $_.MainWindowTitle -match '视频号|��Ƶ' } | Select-Object -First 1
if (-not $target) { $target = Get-Process | Where-Object { $_.ProcessName -eq 'chrome' -and $_.MainWindowTitle } | Select-Object -First 1 }
if (-not $target) { Write-Host 'NO_CHROME_WINDOW'; exit 1 }
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Rect {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
"@
[Win32Rect]::SetForegroundWindow($target.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 500
$rect = New-Object Win32Rect+RECT
[Win32Rect]::GetWindowRect($target.MainWindowHandle, [ref]$rect) | Out-Null
$width = [Math]::Max(1, $rect.Right - $rect.Left)
$height = [Math]::Max(1, $rect.Bottom - $rect.Top)
$outDir = 'D:\workspace\gavin-social-publisher\publish_logs\screenshots'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$out = Join-Path $outDir ('active_chrome_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.png')
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
$graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bmp.Size)
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose(); $bmp.Dispose()
Write-Host $out
