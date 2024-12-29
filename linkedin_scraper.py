import os
import re
import csv
import time
import requests
from github import Github
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from prettytable import PrettyTable
from PyPDF2 import PdfReader
from transformers import pipeline

# LinkedIn Scraper Class
class LinkedInScraper:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.driver = self.setup_driver()
        self.results = []

    def setup_driver(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        service = Service('/usr/local/bin/chromedriver')
        return webdriver.Chrome(service=service, options=options)

    def login(self):
        self.driver.get('https://www.linkedin.com/login')
        time.sleep(2)
        self.driver.find_element(By.ID, 'username').send_keys(self.email)
        self.driver.find_element(By.ID, 'password').send_keys(self.password)
        self.driver.find_element(By.ID, 'password').send_keys(Keys.RETURN)
        time.sleep(5)

    def scrape_profile(self, profile_url):
        self.driver.get(profile_url + 'overlay/contact-info/')
        print(profile_url + 'overlay/contact-info/')
        time.sleep(3)

        profile_data = {
            "Name": "Not Found",
            "Email": "Not Found",
            "GitHub": "Not Found",
            "GitHub Email": "Not Found",
            "Portfolio": "Not Found",
            "Resume": "Not Found"
        }

        try:
            profile_data["Name"] = self.driver.find_element(By.CSS_SELECTOR, '.text-heading-xlarge').text
        except:
            pass

        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, 'a')
            found_email = False
            for link in links:
                url = link.get_attribute('href')
                if url:
                    if "mailto:" in url:
                        profile_data["Email"] = url.split(':')[1]
                        found_email = True
                        print("Email found !!")
                    elif "github.com" in url:
                        print("Email not found in the profile , going to search in Github")
                        profile_data["GitHub"] = url
                        profile_data["GitHub Email"] = GitHubScraper().find_email(url.split('/')[-1])
                    elif re.search(r'portfolio|resume|.io|netlify', url, re.I):
                        print("Found a portfolio , looking for details inside portfolio ")
                        self.driver.get(url)
                        profile_data["Portfolio"] = url
                        time.sleep(2)
                        links = self.driver.find_elements()
                        if "resume" in url.lower():
                            profile_data["Resume"] = url
                       
        except:
            pass

        self.results.append(profile_data)
        return profile_data

    def close(self):
        self.driver.quit()

# GitHub Scraper Class
class GitHubScraper:
    def __init__(self, token=None):
        self.github = Github(token)

    def find_email(self, username):
        try:
            user = self.github.get_user(username)
            email = user.email
            if email:
                return email
            for repo in user.get_repos():
                commits = repo.get_commits()
                for commit in commits[:3]:
                    patch_url = commit.html_url + ".patch"
                    response = requests.get(patch_url)
                    if response.status_code == 200:
                        for line in response.text.splitlines():
                            if "From:" in line and "@" in line:
                                ans = ""
                                found_email = False
                                for str in line:
                                    if(str == '>'):
                                        return ans
                                    if(str == '>'):
                                        found_email = True
                                    if(found_email):
                                        ans+=str
                                return ans
        except:
            pass
        return "GitHub Found, No Email"

# Resume Parser Class
class ResumeParser:
    def parse_resume(self, resume_url):
        response = requests.get(resume_url)
        with open("temp_resume.pdf", "wb") as file:
            file.write(response.content)

        text = self.extract_text_from_pdf("temp_resume.pdf")
        parsed_data = self.extract_contact_info(text)
        os.remove("temp_resume.pdf")
        return parsed_data

    def extract_text_from_pdf(self, file_path):
        reader = PdfReader(file_path)
        return "".join([page.extract_text() for page in reader.pages])

    def extract_contact_info(self, text):
        email = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        phone = re.search(r"\+?\d{10,15}", text)
        return {
            "Email": email.group(0) if email else "Not Found",
            "Phone": phone.group(0) if phone else "Not Found"
        }

# Display Manager
class DisplayManager:
    @staticmethod
    def show_results(data):
        table = PrettyTable()
        table.field_names = ["Name", "Email", "GitHub", "GitHub Email", "Portfolio", "Resume"]
        for entry in data:
            table.add_row([entry.get("Name", ""),
                           entry.get("Email", ""),
                           entry.get("GitHub", ""),
                           entry.get("GitHub Email", ""),
                           entry.get("Portfolio", ""),
                           entry.get("Resume", "")])
        print(table)

    @staticmethod
    def save_to_csv(data, file_name="results.csv"):
        with open(file_name, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=["Name", "Email", "GitHub", "GitHub Email", "Portfolio", "Resume"])
            writer.writeheader()
            writer.writerows(data)

# Main Execution
if __name__ == "__main__":
    linkedin_email = "tanmay.khanna04@gmail.com"
    linkedin_password = "Mainkyubatau@2004"

    linkedin_scraper = LinkedInScraper(linkedin_email, linkedin_password)
    linkedin_scraper.login()

    profile_urls = [
        "https://www.linkedin.com/in/tanish-mittal/"
    ]

    resume_parser = ResumeParser()

    for url in profile_urls:
        profile_data = linkedin_scraper.scrape_profile(url)
        if profile_data.get("Email") != "Not Found":
            break
        if profile_data.get("Resume") != "Not Found":
            contact_info = resume_parser.parse_resume(profile_data["Resume"])
            profile_data.update(contact_info)

    DisplayManager.show_results(linkedin_scraper.results)
    DisplayManager.save_to_csv(linkedin_scraper.results)
    linkedin_scraper.close()
