<#
.SYNOPSIS
    Skrip cadangan pasif untuk mengekspos Mini App @goandalan (http://127.0.0.1:8000)
    sementara lewat Cloudflare Quick Tunnel saat anggota tim baru bergabung.

.NOTES
    - JANGAN jalankan otomatis di background.
    - Pastikan server `python app.py` sudah berjalan di 127.0.0.1:8000 dan `.env` sudah
      mengisi kredensial ADMIN_USN/PASS serta REVIEW_USN/PASS yang kuat.
    - Tekan Ctrl+C untuk langsung menutup tunnel setelah sesi kolaborasi selesai.
#>

[CmdletBinding()]
param(
    [string]$LocalUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$cf = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cf) {
    Write-Host "[ERROR] 'cloudflared' belum terpasang di PATH." -ForegroundColor Red
    Write-Host "Pasang lewat winget: winget install --id Cloudflare.cloudflared" -ForegroundColor Yellow
    Write-Host "Atau unduh dari: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== @goandalan Cloudflare Quick Tunnel (Sesi Sementara) ===" -ForegroundColor Cyan
Write-Host "Target lokal : $LocalUrl" -ForegroundColor Green
Write-Host "Keamanan     : Login Gate + HttpOnly cookie aktif; tutup dengan Ctrl+C bila selesai." -ForegroundColor DarkGray
Write-Host ""

& $cf.Source tunnel --url $LocalUrl --no-autoupdate
