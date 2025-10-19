
```markdown
# eCourts Case List Downloader

Automated tool to download case lists from eCourts India with CAPTCHA solving and PDF generation.

## Features

✅ Single court or bulk download  
✅ Automatic CAPTCHA solving  
✅ Professional PDF generation  
✅ Parallel processing (3 threads)  
✅ Progress tracking  

## Requirements

- Python 3.8+
- Tesseract OCR
- Chrome Browser

## Installation

**1. Install dependencies:**
```

pip install streamlit selenium webdriver-manager pytesseract Pillow beautifulsoup4 reportlab

```

**2. Install Tesseract OCR:**
- **Windows**: Download from [here](https://github.com/UB-Mannheim/tesseract/wiki)
- **macOS**: `brew install tesseract`
- **Linux**: `sudo apt-get install tesseract-ocr`

## Usage

**Start the app:**
```

streamlit run main.py

```

**Steps:**
1. Select State → District → Court Complex
2. Choose date for case lists
3. Select single court or bulk download
4. Click Download button
5. Get PDF or ZIP file

## File Structure

```

├── main.py                  \# Streamlit UI
├── dropdown_manager.py      \# Location dropdowns
├── captcha_handler.py       \# CAPTCHA solver
├── data_extractor.py        \# PDF generator
└── ecourts_pdfs/           \# Output folder

```

## Configuration

Update Tesseract path in `captcha_handler.py`:
```

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

```

## Troubleshooting

**CAPTCHA fails**: Check Tesseract installation with `tesseract --version`  
**Driver error**: Ensure Chrome browser is installed  
**Widget duplication**: Run `streamlit cache clear`

## License

MIT License

---
Made for the legal community ⚖️
```

This simple README follows best practices from the search results while keeping it concise and easy to follow. It covers all essentials: what the project does, how to install it, how to use it, and basic troubleshooting—all in under 100 lines with clear formatting and bullet points for easy scanning.
<span style="display:none">[^1][^2][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://realpython.com/readme-python-project/

[^2]: https://www.makeareadme.com

[^3]: https://gist.github.com/DomPizzie/7a5ff55ffa9081f2de27c315f5018afc

[^4]: https://github.com/othneildrew/Best-README-Template

[^5]: https://packaging.python.org/guides/making-a-pypi-friendly-readme/

[^6]: https://www.pyopensci.org/python-package-guide/tutorials/add-readme.html

[^7]: https://www.youtube.com/watch?v=12trn2NKw5I

[^8]: https://dev.to/scottydocs/how-to-write-a-kickass-readme-5af9

[^9]: https://git.ifas.rwth-aachen.de/templates/ifas-python-template/-/blob/master/README.md

