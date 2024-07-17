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

        # Initialize parent window
        self.parent_window = self.driver.current_window_handle
    
    
    def get_available_banks(self, type='domestic'):
        
        # Remove 'type' parameter and have it set to what the page actually shows
        
        banks = {}
        if type == 'domestic':
            banks = self._get_available_domestic_banks()
            
        return banks
    
    def get_available_dates(self, bank='Z005'):
        self._set_domestic_bank(bank_code=bank)
        
        return self._get_available_monthly_dates()
    
    def get_monthly_balance_sheet(self, bank, month, clean=True):
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
        
        self._switch_to_data_page()
        date = self._extract_date(self.driver.page_source)
        table_df = pd.read_html(StringIO(self.driver.page_source))
        
        time.sleep(0.25)
        self._switch_to_home_page()
        
        if clean:
            return {'date': date,'assets': self.clean_assets(table_df[0]), 'liabilities': table_df[1]}
        
        return {'assets': table_df[0], 'liabilities and equity': table_df[1]}

    def _extract_date(self, page):
        '''
        Extract details from page: date
        page: selenium driver
        '''
        #self.driver.find_element(by=By.CLASS_NAME, "maindiv text-center")
        bs = BeautifulSoup(page, features='lxml')
        rows = bs.find('div', {'class':'maindiv text-center'})
        rows.find_all('p')[1].text.replace('As At', '').strip()

        

    def clean_assets(self, asset):
        # TODO: Automatically check period
        # TODO: only need to load once
        template = self.get_template('balance_sheet', 3)
        template = pd.read_excel("./templates/templates.xlsx", sheet_name='V3', index_col='row_number')

        df = (asset
                .merge(template, left_index=True, right_index=True)
                .assign(
                    item_name = lambda x: x['Item Name'].str.extract('[.)](.*)')[0].str.strip(),
                    total_currency = lambda x: x['Total Currency'].astype('int64').multiply(1000),
                    foreign_currency = lambda x: x['Foreign Currency'].astype('int64').multiply(1000)
                )
                [['Section', 'Category', 'Subcategory', 'item_name', 'foreign_currency', 'total_currency', 'Subset']]
        )
        
        return df
    
    def get_template(self, financial_statement, version):
        PATH = "./templates/"
    
        if financial_statement == 'balance_sheet':
            template = pd.read_excel(PATH + "templates.xlsx", sheet_name=f"V{version}")
        
        return template
    
    def _click_submit(self):
        submit_button = self.driver.find_element(By.ID, "DTIWebPartManager_gwpDTIBankControl1_DTIBankControl1_submitButton")
        submit_button.click()
        time.sleep(0.5)
    
    def _switch_to_data_page(self):
        self.driver.switch_to.window(self.driver.window_handles[1])

    def _switch_to_home_page(self):
        self.driver.switch_to.window(self.driver.window_handles[0])
        
        # Switch to the selected iframe containing the OSFI bank form
        self.driver.switch_to.frame(self._DATA_IFRAME_ID)
    
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

