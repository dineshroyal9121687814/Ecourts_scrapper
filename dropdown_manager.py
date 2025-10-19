"""
eCourts Dropdown Manager Module
Handles all dropdown selections and caching for states, districts, complexes, and courts
"""

import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)

TIMEOUT_SHORT = 10
TIMEOUT_LONG = 15


class DropdownManager:
    """Manages all dropdown operations for eCourts website"""

    def __init__(self, driver):
        self.driver = driver
        self.cache = {}

    def safe_wait(self, element_id, timeout=TIMEOUT_SHORT):
        """Safely wait for element by ID"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, element_id))
            )
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {element_id}")
            return None

    def get_states(self):
        """Fetch all available states"""
        try:
            elem = self.safe_wait("sess_state_code", TIMEOUT_LONG)
            if not elem:
                return {}
            select_elem = Select(elem)
            return {opt.text: opt.get_attribute("value") 
                    for opt in select_elem.options if opt.get_attribute("value") != "0"}
        except Exception as e:
            logger.error(f"Get states failed: {e}")
            return {}

    def get_districts(self, state_code):
        """Fetch districts for given state"""
        cache_key = f"dist_{state_code}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            Select(self.driver.find_element(By.ID, "sess_state_code")).select_by_value(state_code)
            time.sleep(1)
            WebDriverWait(self.driver, TIMEOUT_SHORT).until(
                lambda d: len(Select(d.find_element(By.ID, "sess_dist_code")).options) > 1
            )
            dist_dropdown = Select(self.driver.find_element(By.ID, "sess_dist_code"))
            districts = {opt.text: opt.get_attribute("value") 
                        for opt in dist_dropdown.options if opt.get_attribute("value") != "0"}
            self.cache[cache_key] = districts
            return districts
        except Exception as e:
            logger.error(f"Get districts failed: {e}")
            return {}

    def get_complexes(self, dist_code):
        """Fetch court complexes for given district"""
        cache_key = f"complex_{dist_code}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            Select(self.driver.find_element(By.ID, "sess_dist_code")).select_by_value(dist_code)
            time.sleep(1)
            WebDriverWait(self.driver, TIMEOUT_SHORT).until(
                lambda d: len(Select(d.find_element(By.ID, "court_complex_code")).options) > 1
            )
            complex_dropdown = Select(self.driver.find_element(By.ID, "court_complex_code"))
            complexes = {opt.text: opt.get_attribute("value") 
                        for opt in complex_dropdown.options if opt.get_attribute("value") != "0"}
            self.cache[cache_key] = complexes
            return complexes
        except Exception as e:
            logger.error(f"Get complexes failed: {e}")
            return {}

    def get_courts(self, complex_code):
        """Fetch courts for given complex"""
        cache_key = f"court_{complex_code}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            Select(self.driver.find_element(By.ID, "court_complex_code")).select_by_value(complex_code)
            time.sleep(1)
            WebDriverWait(self.driver, TIMEOUT_SHORT).until(
                lambda d: len(Select(d.find_element(By.ID, "CL_court_no")).options) > 1
            )
            court_dropdown = Select(self.driver.find_element(By.ID, "CL_court_no"))
            courts = {opt.text: opt.get_attribute("value") 
                     for opt in court_dropdown.options 
                     if opt.get_attribute("value") and opt.get_attribute("disabled") is None}
            self.cache[cache_key] = courts
            return courts
        except Exception as e:
            logger.error(f"Get courts failed: {e}")
            return {}

    def select_court(self, court_value):
        """Select court from dropdown"""
        try:
            Select(self.driver.find_element(By.ID, "CL_court_no")).select_by_value(court_value)
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Select court failed: {e}")
            return False

    def select_date(self, selected_date):
        """Set date in form with validation"""
        try:
            date_str = selected_date.strftime("%d-%m-%Y")
            date_input = self.safe_wait("causelist_date", TIMEOUT_LONG)
            if not date_input:
                return False

            self.driver.execute_script("arguments[0].value = '';", date_input)
            time.sleep(0.2)
            self.driver.execute_script(f"arguments[0].value = '{date_str}';", date_input)
            time.sleep(0.3)

            self.driver.execute_script("""
                var element = arguments[0];
                element.dispatchEvent(new Event('change', { bubbles: true }));
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('blur', { bubbles: true }));
            """, date_input)
            time.sleep(0.5)

            actual_value = date_input.get_attribute('value')
            if actual_value != date_str:
                logger.warning(f"Date mismatch: expected {date_str}, got {actual_value}")
                return False
            return True
        except Exception as e:
            logger.error(f"Select date failed: {e}")
            return False

    def setup_navigation(self, state_code, dist_code, complex_code, court_value, selected_date):
        """Complete navigation setup for court selection"""
        try:
            # Select state
            Select(self.driver.find_element(By.ID, "sess_state_code")).select_by_value(state_code)
            time.sleep(1)

            # Wait and select district
            WebDriverWait(self.driver, TIMEOUT_SHORT).until(
                lambda d: len(Select(d.find_element(By.ID, "sess_dist_code")).options) > 1
            )
            Select(self.driver.find_element(By.ID, "sess_dist_code")).select_by_value(dist_code)
            time.sleep(1)

            # Wait and select complex
            WebDriverWait(self.driver, TIMEOUT_SHORT).until(
                lambda d: len(Select(d.find_element(By.ID, "court_complex_code")).options) > 1
            )
            Select(self.driver.find_element(By.ID, "court_complex_code")).select_by_value(complex_code)
            time.sleep(1)

            # Wait and select court
            WebDriverWait(self.driver, TIMEOUT_SHORT).until(
                lambda d: len(Select(d.find_element(By.ID, "CL_court_no")).options) > 1
            )
            if not self.select_court(court_value):
                return False

            time.sleep(1)

            # Set date
            if not self.select_date(selected_date):
                return False

            time.sleep(1)
            return True

        except Exception as e:
            logger.error(f"Setup navigation failed: {e}")
            return False
