import requests
from bs4 import BeautifulSoup
import urllib.parse
from PIL import Image
import io
import json
import random
import logging
import sys
#Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Scraper(object):

    def __init__(self):
        self.url = "https://epanjiyan.rajasthan.gov.in/e-search-page.aspx"

        self.sess = requests.session()
        self.menu = {}
        self.headers  = {
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            # 'Cookie': 'ASP.NET_SessionId=552pq0yh4gll4guaoo4ywu4k; NSC_fqbokjzbo_jqw4=ffffffff094eed2745525d5f4f58455e445a4a423660',
            'Origin': 'https://epanjiyan.rajasthan.gov.in',
            'Referer': 'https://epanjiyan.rajasthan.gov.in/e-search-page.aspx',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'X-MicrosoftAjax': 'Delta=true',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
        }
    

    def solve_captcha(self, captcha_image_url):
        img_url = "https://epanjiyan.rajasthan.gov.in/" + captcha_image_url.replace(" ", "%20")
        response = self.sess.get(img_url, headers= self.headers, timeout=10)
        response.raise_for_status()
        # image = Image.open(io.BytesIO(response.content))
        with open('captcha.png', 'wb') as f:
            f.write(response.content)

        captcha_text = input("check the file captcha.png and Enter the captcha text: ")  # Prompt user to enter the captcha text

        captcha_text = captcha_text.strip()

        return captcha_text

    def parse_table(self, soup):
        table = soup.find("table", id="ContentPlaceHolder1_gridsummary")
        # Extract headers
        headers = [th.get_text(strip=True) for th in table.find("tr").find_all("th")]
        
        data = []
        for row in table.find_all("tr")[1:]:  # skip header row
            cols = row.find_all("td")
            if len(cols) != len(headers):
                continue  # skip if not a data row (like pagination row)
            row_data = {}
            for header, col in zip(headers, cols):
                text = col.get_text(separator=" ", strip=True)
                row_data[header] = text
            data.append(row_data)
        if data:
            with open("scraped_data_e_panjiyan.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
    

    def get_main(self):
        response = self.sess.get(self.url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            self.cookies = self.sess.cookies.get_dict()
            return soup
        
    def get_hidden_fields(self,soup, flag=False):
        """ returns __ hidden parameters present for aspx sites"""
        hidden_params = {}
        if soup.find_all('input', type='hidden'):
            hidden_inputs = soup.find_all('input', type='hidden')
            for hidden in hidden_inputs:
                name = hidden.get('name')
                value = hidden.get('value')
                hidden_params.update({name:value})
        if 'hiddenField' in soup.text and flag:
            hidden = soup.text.split('hiddenField')
            for item in hidden:
                if "__" in item:
                    name = item.split('|')[1].strip().replace('"', '').replace("'", '')
                    value = item.split('|')[2].strip().replace('"', '').replace("'", '')
                    hidden_params.update({name:value})
        if not hidden_params:
            logger.error("No hidden params found ")
        return hidden_params
    
    def call_post(self,payload,timeout):
        response = self.sess.post(self.url, headers=self.headers, data=payload, timeout=timeout)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
        return soup
    
    def get_option_vals(self, soup ,id):
        logger.info(f"Getting data for {id}")
        
        if soup.find('select', {'id': id}):
            try:
                _options = soup.find('select', {'id': id}).find_all('option')
            except Exception as e:
                logger.error(f"No data found for {id}")
            if not _options:
                logger.error(f"No options params found for {id}")
                sys.exit(0)
            _options = [(option.text.strip(),option['value']) for option in _options[1:] if option.text.strip()]
            self.menu.update({id.split('ddl')[-1]: _options})
            

    def get_params(self):
        
        soup = self.get_main()
        data = {
            **self.get_hidden_fields(soup),
            'ctl00$ScriptManager1': 'ctl00$upContent|ctl00$ContentPlaceHolder1$rbtrural',
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$rbtrural',
            'ctl00$ContentPlaceHolder1$a': 'rbtrural',
            'ctl00$ContentPlaceHolder1$ddlDistrict': '- Select District -',
            'ctl00$ContentPlaceHolder1$ddlSRO': '- Select SRO -',
            'ctl00$ContentPlaceHolder1$ddldocument': ' -- Select -- ',
            'ctl00$ContentPlaceHolder1$txtexcutent': '',
            'ctl00$ContentPlaceHolder1$txtclaiment': '',
            'ctl00$ContentPlaceHolder1$txtexecutentadd': '',
            'ctl00$ContentPlaceHolder1$txtprprtyadd': '',
            'ctl00$ContentPlaceHolder1$txtimgcode': '',
            'ctl00$hdnCSRF': '',
            '__ASYNCPOST': 'true'
        }

        soup = self.call_post(data, 10)
        self.get_option_vals(soup, 'ContentPlaceHolder1_ddlDistrict')
        self.get_option_vals(soup, 'ContentPlaceHolder1_ddldocument')
            
        
        data = {**self.get_hidden_fields(soup, flag=True),
                "ctl00$ScriptManager1": "ctl00$upContent|ctl00$ContentPlaceHolder1$ddlDistrict",
                "ScriptManager1_HiddenField": "",
                "ctl00$ContentPlaceHolder1$a": "rbtrural",
                "ctl00$ContentPlaceHolder1$ddlDistrict": "1",
                "ctl00$ContentPlaceHolder1$ddldocument": " -- Select -- ",
                "ctl00$ContentPlaceHolder1$txtexcutent": '',
                "ctl00$ContentPlaceHolder1$txtclaiment": '',
                "ctl00$ContentPlaceHolder1$txtexecutentadd": '',
                "ctl00$ContentPlaceHolder1$txtprprtyadd": '',
                "ctl00$ContentPlaceHolder1$txtimgcode": '',
                "ctl00$hdnCSRF": '',
                "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlDistrict",
                "__ASYNCPOST": "true"}

        soup = self.call_post(data, 10)
        self.get_option_vals(soup, 'ContentPlaceHolder1_ddlTehsil')
        data = {**self.get_hidden_fields(soup, flag=True),
                "ctl00$ScriptManager1": "ctl00$upContent|ctl00$ContentPlaceHolder1$ddlTehsil",
                "ScriptManager1_HiddenField": "",
                "ctl00$ContentPlaceHolder1$a": "rbtrural",
                "ctl00$ContentPlaceHolder1$ddlDistrict": "1",
                "ctl00$ContentPlaceHolder1$ddlTehsil": "1",
                "ctl00$ContentPlaceHolder1$ddldocument": " -- Select -- ",
                "ctl00$ContentPlaceHolder1$txtexcutent": "",
                "ctl00$ContentPlaceHolder1$txtclaiment": "",
                "ctl00$ContentPlaceHolder1$txtexecutentadd": "",
                "ctl00$ContentPlaceHolder1$txtprprtyadd": "",
                "ctl00$ContentPlaceHolder1$txtimgcode": "",
                "ctl00$hdnCSRF": "",
                "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlTehsil",
                "__ASYNCPOST": "true"}
        soup = self.call_post(data, 10)
        self.get_option_vals(soup, 'ContentPlaceHolder1_ddlSRO')
        
        data= {
            **self.get_hidden_fields(soup, flag=True),
            "ctl00$ScriptManager1": "ctl00$upContent|ctl00$ContentPlaceHolder1$ddlSRO",
            "ScriptManager1_HiddenField": "",
            "ctl00$ContentPlaceHolder1$a": "rbtrural",
            "ctl00$ContentPlaceHolder1$ddlDistrict": "1",
            "ctl00$ContentPlaceHolder1$ddlTehsil": "1",
            "ctl00$ContentPlaceHolder1$ddlSRO": "1",
            "ctl00$ContentPlaceHolder1$ddldocument": " -- Select -- ",
            "ctl00$ContentPlaceHolder1$txtexcutent": "",
            "ctl00$ContentPlaceHolder1$txtclaiment": "",
            "ctl00$ContentPlaceHolder1$txtexecutentadd": "",
            "ctl00$ContentPlaceHolder1$txtprprtyadd": "",
            "ctl00$ContentPlaceHolder1$txtimgcode": "",
            "ctl00$hdnCSRF": "",
            "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlSRO",
            "__ASYNCPOST": "true",
        }
        soup = self.call_post(data, 10)
        data = {
             **self.get_hidden_fields(soup, flag=True),
            "ctl00$ScriptManager1": "ctl00$upContent|ctl00$ContentPlaceHolder1$ddldocument",
            "ScriptManager1_HiddenField": "",
            "ctl00$ContentPlaceHolder1$a": "rbtrural",
            "ctl00$ContentPlaceHolder1$ddlDistrict": "1",
            "ctl00$ContentPlaceHolder1$ddlTehsil": "1",
            "ctl00$ContentPlaceHolder1$ddlSRO": "1",
            "ctl00$ContentPlaceHolder1$ddlcolony": "54,1",
            "ctl00$ContentPlaceHolder1$ddldocument": "17",
            "ctl00$ContentPlaceHolder1$txtexcutent": "",
            "ctl00$ContentPlaceHolder1$txtclaiment": "2",
            "ctl00$ContentPlaceHolder1$txtexecutentadd": "",
            "ctl00$ContentPlaceHolder1$txtprprtyadd": "",
            "ctl00$ContentPlaceHolder1$txtimgcode": "",
            "ctl00$hdnCSRF": "",
            "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddldocument",
            "__ASYNCPOST": "true"
            }
        soup = self.call_post(data, 10)
        img_url = soup.find('img', {'id': 'ContentPlaceHolder1_Image1'})['src']
        captcha = self.solve_captcha(img_url)
        data = {
            **self.get_hidden_fields(soup, flag=True),
            'ctl00$ScriptManager1': 'ctl00$upContent|ctl00$ContentPlaceHolder1$btnsummary',
            'ctl00$ContentPlaceHolder1$a': 'rbtrural',
            'ctl00$ContentPlaceHolder1$ddlDistrict': '1',
            'ctl00$ContentPlaceHolder1$ddlTehsil': '1',
            'ctl00$ContentPlaceHolder1$ddlSRO': '1',
            'ctl00$ContentPlaceHolder1$ddlcolony': '54,1',
            'ctl00$ContentPlaceHolder1$ddldocument': '17',
            'ctl00$ContentPlaceHolder1$txtexcutent': '',
            'ctl00$ContentPlaceHolder1$txtclaiment': '2',
            'ctl00$ContentPlaceHolder1$txtexecutentadd': '',
            'ctl00$ContentPlaceHolder1$txtprprtyadd': '',
            'ctl00$ContentPlaceHolder1$txtimgcode': captcha,
            'ctl00$ContentPlaceHolder1$btnsummary': 'View Summary',
            "__ASYNCPOST": "true"
        }
        soup = self.call_post(data, 300)
        self.parse_table(soup)


if __name__ == "__main__":
    ob = Scraper()
    data = ob.get_params()

                