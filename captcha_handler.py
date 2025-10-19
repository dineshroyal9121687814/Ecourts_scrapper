"""
eCourts Captcha Handler - Optimized
Handles CAPTCHA extraction, entry, and form submission
"""

import time
import logging
import pytesseract
from PIL import Image
import io
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
TIMEOUT_SHORT = 10

class CaptchaHandler:
    """Handles CAPTCHA operations"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def clear_modals(self):
        """Close modal dialogs"""
        try:
            self.driver.execute_script("""
                var modal = document.getElementById('validateError');
                if (modal) modal.style.display = 'none';
                document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                document.body.classList.remove('modal-open');
                document.body.style.overflow = 'auto';
            """)
            time.sleep(0.3)
            return True
        except:
            return False
    
    def get_captcha_text(self):
        """Extract CAPTCHA using OCR"""
        try:
            captcha_img = WebDriverWait(self.driver, TIMEOUT_SHORT).until(
                EC.presence_of_element_located((By.ID, "captcha_image"))
            )
            image = Image.open(io.BytesIO(captcha_img.screenshot_as_png))
            text = pytesseract.image_to_string(image, config='--psm 7 --oem 3').strip()
            return text if len(text) > 2 else ""
        except:
            return ""
    
    def enter_captcha(self, captcha_text):
        """Enter CAPTCHA text"""
        try:
            self.clear_modals()
            time.sleep(0.5)
            
            input_box = WebDriverWait(self.driver, TIMEOUT_SHORT).until(
                EC.presence_of_element_located((By.ID, "cause_list_captcha_code"))
            )
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_box)
            self.driver.execute_script("arguments[0].value = '';", input_box)
            time.sleep(0.2)
            
            input_box.send_keys(captcha_text)
            time.sleep(0.3)
            
            return input_box.get_attribute('value') == captcha_text
        except:
            return False
    
    def check_captcha_error(self):
        """Check if CAPTCHA was invalid"""
        try:
            alerts = self.driver.find_elements(By.CLASS_NAME, "alert-danger-cust")
            return any(alert.is_displayed() and "Invalid Captcha" in alert.text for alert in alerts)
        except:
            return False
    
    def submit_case_type(self, case_type):
        """Submit for civil ('civ') or criminal ('cri') cases"""
        try:
            self.clear_modals()
            time.sleep(1)
            self.driver.execute_script(f"submit_causelist('{case_type}');")
            time.sleep(3)
            return not self.check_captcha_error()
        except:
            return False
    
    def process_with_captcha(self, case_type, max_retries=3):
        """Process case type with automatic CAPTCHA retry"""
        for attempt in range(max_retries):
            captcha = self.get_captcha_text()
            if not captcha:
                time.sleep(1)
                continue
            
            if not self.enter_captcha(captcha):
                continue
            
            time.sleep(2)
            if self.submit_case_type(case_type):
                logger.info(f"{case_type} cases processed successfully")
                return True
            
            self.clear_modals()
        
        logger.warning(f"{case_type} cases failed after {max_retries} attempts")
        return False
