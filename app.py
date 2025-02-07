import streamlit as st
import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib.parse
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import base64
from PIL import Image
import io
import openai
from datetime import datetime

class SERPAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key
        openai.api_key = api_key

    def analyze_screenshot(self, image_path):
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')

            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "system",
                        "content": """Vous êtes un expert en analyse de SERP Google. Analysez cette capture d'écran
                        et identifiez tous les éléments (Paid Ads, Organic, PLA, etc.), leur position et calculez
                        la part de visibilité. Retournez les résultats au format JSON."""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "data": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000
            )

            return response.choices[0].message.content
        except Exception as e:
            return str(e)

class GoogleSearchTool:
    def __init__(self):
        self.setup_chrome_options()

    def setup_chrome_options(self):
        self.options = Options()
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument('--headless')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')

    def get_random_user_agent(self):
        chrome_versions = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ]
        return random.choice(chrome_versions)

    def take_screenshot(self, keyword):
        driver = None
        try:
            driver = webdriver.Chrome(options=self.options)
            search_params = {
                'q': keyword,
                'hl': 'fr',
                'gl': 'FR',
                'num': 10
            }
            search_url = f"https://www.google.com/search?{urllib.parse.urlencode(search_params)}"

            driver.get(search_url)
            time.sleep(2)

            try:
                cookie_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.ID, "L2AGLb")))
                cookie_button.click()
            except:
                pass

            screenshot = driver.get_screenshot_as_png()
            return screenshot

        finally:
            if driver:
                driver.quit()

def create_visualization(analysis_results):
    # Créer des visualisations avec Plotly
    # Example (à adapter selon le format de vos résultats):
    df = pd.DataFrame(analysis_results)
    fig = px.bar(df, x='actor', y='visibility_percentage', title='Part de visibilité par acteur')
    return fig

def main():
    st.title("Analyseur de SERP Google")

    # Configuration
    st.sidebar.header("Configuration")
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")

    if not api_key:
        st.warning("Veuillez entrer votre clé API OpenAI pour continuer.")
        return

    # Interface principale
    keyword = st.text_input("Entrez votre mot-clé de recherche")

    if st.button("Lancer l'analyse"):
        if keyword:
            with st.spinner("Capture d'écran en cours..."):
                search_tool = GoogleSearchTool()
                screenshot = search_tool.take_screenshot(keyword)

                # Sauvegarder temporairement le screenshot
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"screenshot_{timestamp}.png"
                with open(screenshot_path, "wb") as f:
                    f.write(screenshot)

                # Afficher le screenshot
                st.image(screenshot, caption="Capture d'écran de la SERP", use_column_width=True)

                # Analyser avec GPT-4
                analyzer = SERPAnalyzer(api_key)
                analysis_results = analyzer.analyze_screenshot(screenshot_path)

                # Afficher les résultats
                st.subheader("Résultats de l'analyse")
                st.json(analysis_results)

                # Créer et afficher les visualisations
                fig = create_visualization(analysis_results)
                st.plotly_chart(fig)

                # Nettoyer
                os.remove(screenshot_path)
        else:
            st.warning("Veuillez entrer un mot-clé de recherche.")

if __name__ == "__main__":
    main()
