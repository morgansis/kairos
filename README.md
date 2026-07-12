# Kairos

Kairos 是為創作者設計的 Windows 桌面媒體整理工具（Media Organizer Pro）。它著重於安全、無損地歸檔照片與影片，提供連拍保護、重複檔案辨識，以及互動式瀏覽報告。

## 功能說明

### 安全整理媒體檔案

- 可選擇多個來源資料夾，集中整理照片與影片。
- 依拍攝日期與時間建立歸檔結構，資料夾名稱使用 `YYYY-MM-DD HH.MM.SS` 格式。
- 支援常見相片、RAW 與影片格式，並保留原始媒體資料。
- 可辨識 Photoshop、Lightroom 等後製來源，將相關媒體歸入 `edited/` 資料夾。

### 連拍與重複檔案保護

- 以檔案大小與分段內容（chunks）進行比對，減少誤判重複檔案的機率。
- 利用 EXIF 拍攝時間與毫秒資訊（`SubSecTimeOriginal`）區分連拍影像。
- 遇到名稱衝突時自動加入編號後綴，避免覆寫既有檔案。

### 互動式媒體報告

- 自動產生 HTML 媒體報告，使用延遲載入（Lazy Load）改善大量檔案的瀏覽體驗。
- 支援全螢幕覆蓋式燈箱瀏覽相片與影片。
- 提供跨平台的檔案清理輔助，協助移除報告或預覽作業產生的暫存檔案。

### 桌面操作體驗

- 提供原生桌面介面、主題配色、進度顯示與處理紀錄。
- 支援安全結束作業，妥善處理使用者中斷與程式關閉情境。

## 專案結構

- `src/kairos/main.py`：主程式。
- `src/kairos/resources/icon.ico`：執行期與封裝用的 Windows 圖示。
- `assets/images/`：非執行期的專案圖片資源。
- `dist/`：本機產生的發布檔，未納入 Git 追蹤。

## 從原始碼執行

```powershell
python3.exe src\kairos\main.py
```

## 發布 Windows 執行檔

先安裝 PyInstaller：

```powershell
python3.exe -m pip install pyinstaller
```

目前專案使用 `src` 結構；請在 repository 根目錄執行以下指令。它會建立單一、無主控台視窗的 `Kairos.exe`，並把視窗圖示一併包入程式：

```powershell
python3.exe -m PyInstaller --noconsole --onefile --icon=src\kairos\resources\icon.ico --add-data "src\kairos\resources\icon.ico;resources" --name="Kairos" --distpath dist src\kairos\main.py
```

若檔案位於原始的平面結構（`icon.ico` 與 `main.py` 同層），可使用下列指令：

```powershell
python3.exe -m PyInstaller --noconsole --onefile --icon=icon.ico --add-data "icon.ico;." --name="Kairos" main.py
```

完成後的執行檔位於 `dist/Kairos.exe`。PyInstaller 產生的 `build/`、`dist/` 與 `.spec` 檔已由 `.gitignore` 排除。
