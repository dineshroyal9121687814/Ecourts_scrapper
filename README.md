
Automated Streamlit application to download cause lists from eCourts India with intelligent CAPTCHA solving and professional PDF generation.

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/dineshroyal9121687814/Ecourts_scrapper.git
cd Ecourts_scrapper
```

### 2. Install Python Dependencies
```
pip install -r requirements.txt
```

### 3. Install Tesseract OCR

**Windows:**
- Download from https://github.com/UB-Mannheim/tesseract/wiki
- Install to C:\\\\Program Files\\\\Tesseract-OCR
- If installed elsewhere, update path in captcha_handler.py:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Path\To\Tesseract-OCR\tesseract.exe'
```

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### 4. Run Application
```bash
streamlit run main.py
```

The app will open in your browser at http://localhost:8501.

---

## 📖 Usage

1. **Select Location:** Choose State → District → Court Complex from dropdowns
2. **Select Date:** Pick date for case lists (past 365 days to future 60 days)
3. **Choose Mode:** 
   - Single Court: Download one court's case list
   - Bulk Download: Download all courts in selected complex
4. **Download:** Click button to get PDF or ZIP file

---

## ⚙️ Configuration

**Windows Only:** If Tesseract is installed in a different location, update path in captcha_handler.py:
```python
pytesseract.pytesseract.tesseract_cmd = r'YOUR_TESSERACT_PATH\tesseract.exe'
```

---

## 📦 Requirements

```text
streamlit>=1.28.0
selenium>=4.15.0
webdriver-manager>=4.0.0
pytesseract>=0.3.10
Pillow>=10.0.0
beautifulsoup4>=4.12.0
reportlab>=4.0.0
```

**Note:** Chrome browser required for Selenium automation.

---

## 📁 Project Structure

```text
├── main.py                 # Streamlit UI application
├── dropdown_manager.py     # Location dropdown handler
├── captcha_handler.py      # CAPTCHA solver
├── data_extractor.py       # PDF generator
├── requirements.txt        # Python dependencies
└── ecourts_pdfs/           # Output directory (auto-created)
```

---

## ✨ Features

- ✅ Automated CAPTCHA solving with OCR
- ✅ Single court or bulk download modes
- ✅ Parallel processing (3 concurrent downloads)
- ✅ Professional PDF generation with formatting
- ✅ Real-time progress tracking
- ✅ Automatic ZIP archive creation
- ✅ Smart caching to reduce API calls

---

## 🐛 Troubleshooting

**CAPTCHA extraction fails:**
```bash
tesseract --version  # Verify installation
```

**Browser driver error:**
- Ensure Chrome browser is installed
- WebDriver Manager will auto-download ChromeDriver

