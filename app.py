import streamlit as st
import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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
import json

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
                        la part de visibilité. Retournez les résultats au format JSON avec la structure suivante:
                        {
                            "actors": [
                                {
                                    "name": "nom_acteur",
                                    "visibility_percentage": nombre,
                                    "elements": [
                                        {
                                            "type": "type_element",
                                            "position": nombre
                                        }
                                    ]
                                }
                            ],
                            "element_types": [
                                {
                                    "type": "type_element",
                                    "count": nombre,
                                    "visibility_percentage": nombre
                                }
                            ]
                        }"""
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

            # Convertir la réponse en JSON
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            st.error(f"Erreur lors de l'analyse: {str(e)}")
            return None

class GoogleSearchTool:
    def __init__(self):
        self.setup_chrome_options()

    def setup_chrome_options(self):
        self.options = Options()
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument('--headless=new')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option('useAutomationExtension', False)

    def get_random_user_agent(self):
        chrome_versions = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ]
        return random.choice(chrome_versions)

    def take_screenshot(self, keyword):
        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.options)

            search_params = {
                'q': keyword,
                'hl': 'fr',
                'gl': 'FR',
                'num': 10
            }
            search_url = f"https://www.google.com/search?{urllib.parse.urlencode(search_params)}"

            driver.get(search_url)
            time.sleep(3)  # Augmenté pour assurer le chargement complet

            try:
                cookie_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "L2AGLb")))
                cookie_button.click()
                time.sleep(1)
            except:
                pass

            # Faire défiler la page pour charger tout le contenu
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            # Revenir en haut de la page
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            screenshot = driver.get_screenshot_as_png()
            return screenshot

        except Exception as e:
            st.error(f"Erreur lors de la capture d'écran: {str(e)}")
            return None
        finally:
            if driver:
                driver.quit()

def create_visualization(analysis_results):
    if not analysis_results:
        return None

    # Créer un DataFrame pour les acteurs
    actors_df = pd.DataFrame([
        {
            'Acteur': actor['name'],
            'Visibilité (%)': actor['visibility_percentage']
        }
        for actor in analysis_results['actors']
    ])

    # Créer un DataFrame pour les types d'éléments
    elements_df = pd.DataFrame([
        {
            'Type': element['type'],
            'Visibilité (%)': element['visibility_percentage']
        }
        for element in analysis_results['element_types']
    ])

    # Créer les graphiques
    fig_actors = px.bar(actors_df,
                       x='Acteur',
                       y='Visibilité (%)',
                       title='Part de visibilité par acteur')

    fig_elements = px.pie(elements_df,
                         values='Visibilité (%)',
                         names='Type',
                         title='Répartition des types d\'éléments')

    return fig_actors, fig_elements

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

                if screenshot:
                    # Sauvegarder temporairement le screenshot
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = f"screenshot_{timestamp}.png"
                    with open(screenshot_path, "wb") as f:
                        f.write(screenshot)

                    # Afficher le screenshot
                    st.image(screenshot, caption="Capture d'écran de la SERP", use_column_width=True)

                    # Analyser avec GPT-4
                    with st.spinner("Analyse en cours..."):
                        analyzer = SERPAnalyzer(api_key)
                        analysis_results = analyzer.analyze_screenshot(screenshot_path)

                        if analysis_results:
                            # Afficher les résultats
                            st.subheader("Résultats de l'analyse")
                            st.json(analysis_results)

                            # Créer et afficher les visualisations
                            fig_actors, fig_elements = create_visualization(analysis_results)
                            if fig_actors and fig_elements:
                                st.plotly_chart(fig_actors)
                                st.plotly_chart(fig_elements)

                    # Nettoyer
                    os.remove(screenshot_path)
        else:
            st.warning("Veuillez entrer un mot-clé de recherche.")

if __name__ == "__main__":
    main()
