from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO


class OSFICrawler():
    """
    Web crawler and scraper for OSFI's public data portal.

    ...

    Attributes
    ----------
    URL : str
        URL to OSFI's data portal.
    category : str
        the category of financial institution's to investigate

    Methods
    -------


    """
    def __init__(self, category="financial-data-banks"):
        self.URL = "https://www.osfi-bsif.gc.ca/en/data-forms/financial-data/" + category
        
        # id that contains the iframe with the table
        self._DATA_IFRAME_ID = 'ctl00_ctl61_g_69670f48_11c6_4626_9f60_e63007ee266c_FINDATIFrame' 
        
        options = webdriver.ChromeOptions()
        options.add_argument("headless")

        self.driver = webdriver.Chrome(service = Service(ChromeDriverManager().install()), options=options)
        
        self.driver.get(self.URL)
        
        # Switch to the selected iframe containing the OSFI bank form
        self.driver.switch_to.frame(self._DATA_IFRAME_ID)
    
    
    
    def get_available_banks(self, type='domestic'):
        
        # Remove 'type' parameter and have it set to what the page actually shows
        
        banks = {}
        if type == 'domestic':
            banks = self._get_available_domestic_banks()
            
        return banks
    
    def get_available_dates(self):
        return self._get_available_monthly_dates()
    
    def get_monthly_balance_sheet(self, bank, month):
        '''
        Both are bank code and month code
        
        Example:
        get_monthly_balance_sheet(bank='AW', month='1 - 2000') returns Bridgewater's balance sheet for January 2000
        
        
        Returns:
            dataframe
        '''
        
        self._set_month(month)
        self._set_domestic_bank(bank)
        self._click_submit()
        self._change_page()

        table_df = pd.read_html(StringIO(self.driver.page_source))
        time.sleep(0.25)
        return {'assets': table_df[0], 'liabilities and equity': table_df[1]}

        
    
    def _click_submit(self):
        submit_button = self.driver.find_element(By.ID, "DTIWebPartManager_gwpDTIBankControl1_DTIBankControl1_submitButton")
        submit_button.click()
        time.sleep(0.5)
    
    def _change_page(self):
        p = self.driver.current_window_handle

        #get first child window
        chwd = self.driver.window_handles

        for w in chwd:
        #switch focus to child window
            if(w!=p):
                self.driver.switch_to.window(w)
    
    
    def _monthly_selector(self):
        
        return Select(
            self.driver.find_element(By.ID, "DTIWebPartManager_gwpDTIBankControl1_DTIBankControl1_dtiReportCriteria_monthlyDatesDropDownList")
        )
            
    def _set_month(self, date):
        '''
        In format 'M - YYYY'
        '''
        self._monthly_selector().select_by_value(date)
    
    def _get_available_monthly_dates(self):
        
        date_list = self._monthly_selector().options

        monthly_dict = {}
        for item in date_list:
            monthly_dict[item.get_attribute('value')] =  item.text
        
        return monthly_dict

    
    def _domestic_bank_selector(self):
        return Select(
            self.driver.find_element(By.ID, "DTIWebPartManager_gwpDTIBankControl1_DTIBankControl1_institutionTypeCriteria_institutionsDropDownList")
        )
    
    def _get_available_domestic_banks(self):
        
        bank_list = self._domestic_bank_selector().options
        
        bank_dict = {}
        for item in bank_list:
            bank_dict[item.get_attribute('value')] =  item.text
        
        return bank_dict

    def _set_domestic_bank(self, bank_code):
        '''
        Accepts bank code
        '''
        self._domestic_bank_selector().select_by_value(bank_code)

