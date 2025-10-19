import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import logging
from datetime import date, timedelta
from pathlib import Path
import zipfile
import concurrent.futures
from dropdown_manager import DropdownManager
from captcha_handler import CaptchaHandler
from data_extractor import DataExtractor, CourtProcessor

# ==================== CONFIG ====================
st.set_page_config(page_title="eCourts Bulk Downloader", layout="wide", initial_sidebar_state="collapsed")
logging.basicConfig(level=logging.WARNING)

OUTPUT_DIR = Path("ecourts_pdfs")
OUTPUT_DIR.mkdir(exist_ok=True)
MAX_WORKERS = 3
TIMEOUT_LONG = 15
ECOURTS_URL = "https://services.ecourts.gov.in/ecourtindia_v6/?p=cause_list/"

# ==================== STYLING ====================
st.markdown("""
<style>
    .main-title {font-size: 2.5rem; font-weight: bold; color: #1f77b4; text-align: center; margin-bottom: 2rem;}
    .section-header {font-size: 1.3rem; font-weight: 600; color: #2c3e50; margin-top: 1.5rem; border-bottom: 2px solid #1f77b4; padding-bottom: 0.5rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">⚖️ eCourts Case List Downloader</div>', unsafe_allow_html=True)

# ==================== DRIVER ====================
def create_new_driver():
    """Create Chrome driver instance"""
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--headless")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(TIMEOUT_LONG)
        driver.implicitly_wait(2)
        return driver
    except Exception as e:
        st.error(f"Driver creation failed: {e}")
        return None

@st.cache_resource(show_spinner=False)
def get_main_driver():
    """Initialize main driver (CACHED)"""
    driver = create_new_driver()
    if driver:
        driver.get(ECOURTS_URL)
        time.sleep(2)
    return driver

# ==================== BULK PROCESSING ====================
def process_single_court(court_info, selected_date, max_retries=3):
    """Process single court with own driver - retry 3 times on failure"""
    for attempt in range(1, max_retries + 1):
        driver = None
        try:
            driver = create_new_driver()
            if not driver:
                if attempt == max_retries:
                    return {'status': 'error', 'court': court_info['court_name'], 'error': 'Tried multiple times, unable to get. Try refreshing page and try again.'}
                time.sleep(1)
                continue

            driver.get(ECOURTS_URL)
            time.sleep(2)

            dropdown_mgr = DropdownManager(driver)
            captcha_handler = CaptchaHandler(driver)
            court_processor = CourtProcessor(driver)

            if not dropdown_mgr.setup_navigation(
                court_info['state_code'], court_info['dist_code'],
                court_info['complex_code'], court_info['court_value'], selected_date
            ):
                if attempt == max_retries:
                    return {'status': 'error', 'court': court_info['court_name'], 'error': 'Tried multiple times, unable to get. Try refreshing page and try again.'}
                time.sleep(1)
                continue

            civil_data, criminal_data = court_processor.process_cases(captcha_handler)
            safe_filename = re.sub(r'[<>:"/\\|?*]', '_', court_info['court_name'])
            pdf_path = OUTPUT_DIR / f"{safe_filename}_{selected_date.strftime('%Y%m%d')}.pdf"

            if DataExtractor.create_pdf(civil_data, criminal_data, str(pdf_path), court_info['court_name']):
                return {'status': 'success', 'court': court_info['court_name'], 'file': str(pdf_path)}
            
            if attempt == max_retries:
                return {'status': 'error', 'court': court_info['court_name'], 'error': 'Tried multiple times, unable to get. Try refreshing page and try again.'}
            time.sleep(1)
            
        except Exception as e:
            if attempt == max_retries:
                return {'status': 'error', 'court': court_info['court_name'], 'error': 'Tried multiple times, unable to get. Try refreshing page and try again.'}
            time.sleep(1)
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    return {'status': 'error', 'court': court_info['court_name'], 'error': 'Tried multiple times, unable to get. Try refreshing page and try again.'}

# ==================== INIT SESSION STATE ====================
def init_session():
    """Initialize session state"""
    defaults = {
        "initialized": False, "driver": None, "dropdown_manager": None,
        "states": {}, "current_state": None, "current_district": None,
        "current_complex": None, "current_court": None,
        "selected_date": date.today(), "data_cache": {}
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if not st.session_state.initialized:
        with st.spinner("Initializing browser..."):
            st.session_state.driver = get_main_driver()
            if st.session_state.driver:
                st.session_state.dropdown_manager = DropdownManager(st.session_state.driver)
                st.session_state.states = st.session_state.dropdown_manager.get_states()
                if st.session_state.states:
                    st.session_state.current_state = list(st.session_state.states.keys())[0]
                    st.session_state.initialized = True
                    st.rerun()
        
        if not st.session_state.initialized:
            st.error("❌ Failed to initialize. Please refresh the page.")
            st.stop()

init_session()
dropdown_manager = st.session_state.dropdown_manager
driver = st.session_state.driver
districts = dropdown_manager.get_districts(st.session_state.states[st.session_state.current_state])

# ==================== DATA LOADING ====================
def load_complexes(state_name, dist_name):
    """Load complexes with caching"""
    cache_key = f"complex_{state_name}_{dist_name}"
    if cache_key not in st.session_state.data_cache:
        dist_code = districts[dist_name]
        st.session_state.data_cache[cache_key] = dropdown_manager.get_complexes(dist_code)
    return st.session_state.data_cache[cache_key]

def load_courts(state_name, dist_name, complex_name):
    """Load courts with caching"""
    cache_key = f"court_{state_name}_{dist_name}_{complex_name}"
    if cache_key not in st.session_state.data_cache:
        complexes = load_complexes(state_name, dist_name)
        complex_code = complexes[complex_name]
        st.session_state.data_cache[cache_key] = dropdown_manager.get_courts(complex_code)
    return st.session_state.data_cache[cache_key]

# ==================== UI - DROPDOWNS ====================
st.markdown('<div class="section-header">📍 Location Selection</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    state_options = list(st.session_state.states.keys())
    selected_state = st.selectbox("🗺️ State", state_options, key="state_select")
    if selected_state != st.session_state.current_state:
        st.session_state.current_state = selected_state
        st.session_state.current_district = None
        st.session_state.current_complex = None
        st.session_state.current_court = None
        st.rerun()

with col2:
    districts = dropdown_manager.get_districts(st.session_state.states[st.session_state.current_state])
    if st.session_state.current_district is None:
        st.session_state.current_district = list(districts.keys())[0]
    
    selected_district = st.selectbox("🏛️ District", list(districts.keys()), 
                                      index=list(districts.keys()).index(st.session_state.current_district), key="dist_select")
    if selected_district != st.session_state.current_district:
        st.session_state.current_district = selected_district
        st.session_state.current_complex = None
        st.session_state.current_court = None
        st.rerun()

col3, col4 = st.columns(2)

with col3:
    complexes = load_complexes(st.session_state.current_state, st.session_state.current_district)
    if st.session_state.current_complex is None:
        st.session_state.current_complex = list(complexes.keys())[0]
    
    selected_complex = st.selectbox("🏢 Court Complex", list(complexes.keys()),
                                     index=list(complexes.keys()).index(st.session_state.current_complex), key="complex_select")
    if selected_complex != st.session_state.current_complex:
        st.session_state.current_complex = selected_complex
        st.session_state.current_court = None
        st.rerun()

with col4:
    st.write("")

courts = load_courts(st.session_state.current_state, st.session_state.current_district, st.session_state.current_complex)

# ==================== DATE & MODE ====================
st.markdown('<div class="section-header">📅 Date Selection</div>', unsafe_allow_html=True)
max_date = date.today() + timedelta(days=60)
selected_date = st.date_input("Select date", date.today(), 
                               min_value=date.today() - timedelta(days=365), max_value=max_date)
st.session_state.selected_date = selected_date

st.markdown('<div class="section-header">📥 Download Mode</div>', unsafe_allow_html=True)
download_mode = st.radio("", ["📄 Single Court", "📚 All Courts (Bulk Download)"], horizontal=True, label_visibility="collapsed")

st.markdown("---")

# ==================== SINGLE COURT MODE ====================
if download_mode == "📄 Single Court":
    if st.session_state.current_court is None:
        st.session_state.current_court = list(courts.keys())[0]
    
    selected_court = st.selectbox("Select Court", list(courts.keys()), 
                                   index=list(courts.keys()).index(st.session_state.current_court))
    st.session_state.current_court = selected_court

    st.info(f"📅 **Date:** {selected_date.strftime('%d-%m-%Y')} | ⚖️ **Court:** {selected_court}")

    if st.button("🚀 Download PDF", type="primary", use_container_width=True):
        with st.spinner("🔄 Processing..."):
            try:
                captcha_handler = CaptchaHandler(driver)
                court_processor = CourtProcessor(driver)

                if not dropdown_manager.setup_navigation(
                    st.session_state.states[st.session_state.current_state],
                    districts[st.session_state.current_district],
                    complexes[st.session_state.current_complex],
                    courts[selected_court], selected_date
                ):
                    st.error("❌ Navigation failed")
                    st.stop()

                civil_data, criminal_data = court_processor.process_cases(captcha_handler)
                safe_filename = re.sub(r'[<>:"/\\|?*]', '_', selected_court)
                pdf_filename = f"{safe_filename}_{selected_date.strftime('%Y%m%d')}.pdf"

                if DataExtractor.create_pdf(civil_data, criminal_data, pdf_filename, selected_court):
                    st.success("✅ PDF generated successfully!")
                    with open(pdf_filename, "rb") as f:
                        st.download_button("📥 Download PDF", f.read(), pdf_filename, 
                                         "application/pdf", use_container_width=True, type="primary")
                else:
                    st.error("❌ PDF generation failed")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# ==================== BULK MODE ====================
else:
    st.info(f"📊 **Total Courts:** {len(courts)} | 📅 **Date:** {selected_date.strftime('%d-%m-%Y')}")
    clear_old = st.checkbox("🗑️ Clear old PDF files", value=True)

    if st.button("🚀 Download All Courts", type="primary", use_container_width=True):
        if clear_old:
            for f in OUTPUT_DIR.glob("*.pdf"):
                f.unlink(missing_ok=True)
            for f in OUTPUT_DIR.glob("*.zip"):
                f.unlink(missing_ok=True)

        court_info_list = [{
            'state_code': st.session_state.states[st.session_state.current_state],
            'dist_code': districts[st.session_state.current_district],
            'complex_code': complexes[st.session_state.current_complex],
            'court_value': court_value,
            'court_name': court_name
        } for court_name, court_value in courts.items()]

        total_courts = len(court_info_list)
        progress_bar = st.progress(0)
        status_text = st.empty()
        current_court_text = st.empty()

        results, completed, successful_files = [], 0, []
        status_text.markdown(f"**Progress: 0/{total_courts}** (0.0%)")

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(process_single_court, info, selected_date): info['court_name'] 
                      for info in court_info_list}

            for future in concurrent.futures.as_completed(futures):
                court_name = futures[future]
                try:
                    result = future.result(timeout=180)
                    results.append(result)
                    completed += 1

                    if result['status'] == 'success':
                        successful_files.append(result['file'])
                        current_court_text.success(f"✅ {court_name}")
                    else:
                        current_court_text.error(f"❌ {court_name}: {result.get('error', 'Unknown')}")

                    progress = completed / total_courts
                    progress_bar.progress(progress)
                    status_text.markdown(f"**Progress: {completed}/{total_courts}** ({progress*100:.1f}%)")
                except concurrent.futures.TimeoutError:
                    results.append({'status': 'error', 'court': court_name, 'error': 'Timeout'})
                    completed += 1
                    current_court_text.error(f"❌ Timeout: {court_name}")
                except Exception as e:
                    results.append({'status': 'error', 'court': court_name, 'error': str(e)})
                    completed += 1

                time.sleep(0.5)

        # Summary
        st.markdown("---")
        st.markdown('<div class="section-header">📈 Summary</div>', unsafe_allow_html=True)

        success_count = sum(1 for r in results if r['status'] == 'success')
        failed_count = total_courts - success_count

        col1, col2, col3 = st.columns(3)
        col1.metric("Total", total_courts)
        col2.metric("✅ Success", success_count)
        col3.metric("❌ Failed", failed_count)

        if success_count > 0:
            st.success(f"🎉 Generated {success_count} PDF(s)")

            zip_filename = f"ecourts_{st.session_state.current_complex.replace(' ', '_')}_{selected_date.strftime('%Y%m%d')}.zip"
            zip_path = OUTPUT_DIR / zip_filename

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for pdf in successful_files:
                    zipf.write(pdf, Path(pdf).name)

            with open(zip_path, "rb") as f:
                st.download_button(f"📥 Download All {success_count} PDFs (ZIP)", f.read(), 
                                 zip_filename, "application/zip", use_container_width=True, type="primary")

            with st.expander(f"📄 Files ({success_count})"):
                for pdf in successful_files:
                    st.text(f"✅ {Path(pdf).name}")

        if failed_count > 0:
            with st.expander(f"⚠️ Failed ({failed_count})"):
                for r in results:
                    if r['status'] != 'success':
                        st.text(f"❌ {r['court']}: {r.get('error', 'Unknown')}")

st.markdown("---")
st.caption("💡 Each court uses independent browser | ⚙️ 3 parallel threads | 📁 Saved to 'ecourts_pdfs'")