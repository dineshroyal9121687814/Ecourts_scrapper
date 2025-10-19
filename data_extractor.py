"""
eCourts Data Extractor Module
Handles data extraction from web pages and PDF generation
"""

import time
import re
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

logger = logging.getLogger(__name__)

TIMEOUT_SHORT = 10
TIMEOUT_LONG = 15


class DataExtractor:
    """Handles data extraction and PDF generation"""

    def __init__(self, driver):
        self.driver = driver

    def extract_case_data(self):
        """Extract case data from loaded page"""
        try:
            WebDriverWait(self.driver, TIMEOUT_LONG).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            if not self.safe_wait("dispTable", TIMEOUT_SHORT):
                return None, None

            time.sleep(2)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            heading_data = {'court_name': '', 'judge_info': '', 'designation': '', 'case_type_date': ''}

            for center in soup.find_all('center'):
                for span in center.find_all('span'):
                    text = span.get_text(strip=True)
                    if 'District' in text or 'Courts' in text:
                        heading_data['court_name'] = text
                    elif 'In the court of' in text:
                        heading_data['judge_info'] = text.replace('In the court of', '').replace(':', '').strip()
                    elif 'JUDGE' in text or 'MAGISTRATE' in text:
                        heading_data['designation'] = text

                full_text = center.get_text(separator=' ', strip=True)
                if 'Cases Listed on' in full_text:
                    match = re.search(r'(Civil|Criminal)\s+Cases\s+Listed\s+on\s+[\d\-]+', full_text)
                    if match:
                        heading_data['case_type_date'] = match.group(0)

            table = soup.find('table', {'id': 'dispTable'})
            if not table:
                return heading_data, None

            table_data = []
            for row in table.find_all('tr'):
                cols = row.find_all(['td', 'th'])
                if not cols:
                    continue

                first_col = cols[0]
                colspan = int(first_col.get('colspan', '1'))

                if colspan > 1:
                    table_data.append({'type': 'header', 'text': first_col.get_text(strip=True)})
                else:
                    row_data = [col.get_text(strip=True) for col in cols]
                    if any(row_data):
                        table_data.append({'type': 'data', 'cells': row_data})

            return heading_data, table_data if table_data else None

        except Exception as e:
            logger.error(f"Extract case data failed: {e}")
            return None, None

    def safe_wait(self, element_id, timeout=TIMEOUT_SHORT):
        """Safely wait for element by ID"""
        try:
            from selenium.webdriver.support import expected_conditions as EC
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, element_id))
            )
        except Exception:
            return None

    @staticmethod
    def create_pdf(civil_data, criminal_data, filename, court_name=""):
        """Generate PDF with case data

        Args:
            civil_data: Tuple of (heading_data, table_data) for civil cases
            criminal_data: Tuple of (heading_data, table_data) for criminal cases
            filename: Output PDF filename
            court_name: Name of the court for title

        Returns:
            bool: True if PDF created successfully
        """
        try:
            doc = SimpleDocTemplate(str(filename), pagesize=landscape(A4), 
                                  leftMargin=0.5*inch, rightMargin=0.5*inch,
                                  topMargin=0.5*inch, bottomMargin=0.5*inch)
            story = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                fontSize=18, textColor=colors.HexColor('#4866af'), spaceAfter=10,
                alignment=TA_CENTER, fontName='Helvetica-Bold')

            court_style = ParagraphStyle('CourtStyle', parent=styles['Normal'],
                fontSize=12, textColor=colors.HexColor('#4866af'), spaceAfter=5,
                alignment=TA_CENTER, fontName='Helvetica-Bold')

            judge_style = ParagraphStyle('JudgeStyle', parent=styles['Normal'],
                fontSize=11, spaceAfter=5, alignment=TA_CENTER, fontName='Helvetica-Bold')

            date_style = ParagraphStyle('DateStyle', parent=styles['Normal'],
                fontSize=10, spaceAfter=20, alignment=TA_CENTER)

            cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8, leading=10)

            no_cases_style = ParagraphStyle('NoCases', parent=styles['Normal'],
                fontSize=12, textColor=colors.red, spaceAfter=20,
                alignment=TA_CENTER, fontName='Helvetica-Bold')

            story.append(Paragraph(f"eCourts Case List - {court_name}", title_style))
            story.append(Spacer(1, 0.2*inch))

            for case_type, case_data in [("CIVIL CASES", civil_data), ("CRIMINAL CASES", criminal_data)]:
                if case_type == "CRIMINAL CASES" and story:
                    story.append(PageBreak())

                story.append(Paragraph(case_type, title_style))
                story.append(Spacer(1, 0.1*inch))

                if not case_data or not case_data[0]:
                    story.append(Paragraph(f"No {case_type.lower()} found", no_cases_style))
                    continue

                heading, table_data = case_data

                if heading.get('court_name'):
                    story.append(Paragraph(heading['court_name'], court_style))
                if heading.get('judge_info'):
                    story.append(Paragraph(f"In the court of: {heading['judge_info']}", judge_style))
                if heading.get('designation'):
                    story.append(Paragraph(heading['designation'], judge_style))
                if heading.get('case_type_date'):
                    story.append(Paragraph(heading['case_type_date'], date_style))

                story.append(Spacer(1, 0.1*inch))

                if table_data and len(table_data) > 1:
                    processed_data = []
                    for row in table_data:
                        if row['type'] == 'header':
                            processed_data.append([Paragraph(f"<b>{row['text']}</b>", cell_style), '', '', ''])
                        else:
                            wrapped_row = [Paragraph(str(cell), cell_style) if cell else '' 
                                         for cell in row['cells'][:4]]
                            while len(wrapped_row) < 4:
                                wrapped_row.append('')
                            processed_data.append(wrapped_row)

                    t = Table(processed_data, colWidths=[0.7*inch, 2.2*inch, 3.5*inch, 2.2*inch], repeatRows=1)

                    table_style = [
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4866af')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('TOPPADDING', (0, 0), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ]

                    for idx, row in enumerate(table_data):
                        if row['type'] == 'header':
                            table_style.extend([
                                ('SPAN', (0, idx), (-1, idx)),
                                ('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#e6f2ff')),
                                ('TEXTCOLOR', (0, idx), (-1, idx), colors.HexColor('#3880d4')),
                                ('FONTNAME', (0, idx), (-1, idx), 'Helvetica-Bold'),
                                ('ALIGN', (0, idx), (-1, idx), 'LEFT'),
                                ('FONTSIZE', (0, idx), (-1, idx), 9),
                            ])

                    t.setStyle(TableStyle(table_style))
                    story.append(t)
                else:
                    story.append(Paragraph(f"No {case_type.lower()} found", no_cases_style))

            doc.build(story)
            return True

        except Exception as e:
            logger.error(f"PDF creation failed: {e}")
            return False


class CourtProcessor:
    """Processes court data including CAPTCHA handling and data extraction"""

    def __init__(self, driver):
        self.driver = driver
        self.extractor = DataExtractor(driver)

    def process_cases(self, captcha_handler, max_retries=3):
        """Process both civil and criminal cases

        Args:
            captcha_handler: CaptchaHandler instance
            max_retries: Maximum retry attempts per case type

        Returns:
            Tuple: (civil_data, criminal_data)
        """
        civil_data = None
        criminal_data = None

        # Process Civil Cases
        if captcha_handler.process_with_captcha('civ', max_retries):
            civil_data = self.extractor.extract_case_data()

        time.sleep(2)

        # Process Criminal Cases
        if captcha_handler.process_with_captcha('cri', max_retries):
            criminal_data = self.extractor.extract_case_data()

        return civil_data, criminal_data
