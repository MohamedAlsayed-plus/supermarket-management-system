@echo off
REM Build the Windows app locally (run this on a Windows machine).
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller SupermarketDB.spec --clean --noconfirm
echo.
echo Done. Run: dist\SupermarketDB\SupermarketDB.exe
pause
