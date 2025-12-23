# Script de instalación de dependencias para detección de líneas
# Instala OpenCV y NumPy necesarios para document_analyzer.py

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Instalando dependencias para detección de líneas" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📦 Instalando NumPy..." -ForegroundColor Yellow
pip install numpy

Write-Host ""
Write-Host "📦 Instalando OpenCV..." -ForegroundColor Yellow
pip install opencv-python

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "  ✅ Instalación completada" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Dependencias instaladas:" -ForegroundColor White
pip list | Select-String -Pattern "opencv|numpy|pillow"
