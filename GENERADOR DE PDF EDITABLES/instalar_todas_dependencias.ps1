# Script de instalación completa de dependencias para PDF Master Pro
# Instala todas las librerías necesarias para ejecutar la aplicación

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  PDF MASTER PRO - Instalación de Dependencias" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

$dependencias = @(
    "customtkinter",
    "PyMuPDF",
    "opencv-python",
    "numpy",
    "reportlab",
    "pypdf",
    "Pillow"
)

$total = $dependencias.Count
$actual = 0

foreach ($dep in $dependencias) {
    $actual++
    Write-Host "[$actual/$total] 📦 Instalando $dep..." -ForegroundColor Yellow
    pip install $dep --quiet
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ $dep instalado correctamente" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Error instalando $dep" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "===========================================================" -ForegroundColor Green
Write-Host "  ✅ Instalación completada" -ForegroundColor Green
Write-Host "===========================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Dependencias instaladas:" -ForegroundColor White
pip list | Select-String -Pattern "customtkinter|PyMuPDF|opencv|numpy|reportlab|pypdf|Pillow"

Write-Host ""
Write-Host "Para ejecutar la aplicación:" -ForegroundColor Cyan
Write-Host "  python PDF_MASTER_PRO.py" -ForegroundColor Yellow
Write-Host ""
