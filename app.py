import streamlit as st
import os
import time
import random
import undetected_chromedriver as uc
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

class GoogleSearchTool:
    def __init__(self):
        self.setup_chrome_options()

    def setup_chrome_options(self):
        self.options = uc.ChromeOptions()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--window-size=1920,1080')

    def take_screenshot(self, keyword):
        driver = None
        try:
            driver = uc.Chrome(options=self.options)

            search_params = {
                'q': keyword,
                'hl': 'fr',
                'gl': 'FR',
                'num': 10
            }
            search_url = f"https://www.google.com/search?{urllib.parse.urlencode(search_params)}"

            driver.get(search_url)
            time.sleep(3)

            try:
                cookie_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "L2AGLb")))
                cookie_button.click()
                time.sleep(1)
            except:
                pass

            # Scroll pour charger tout le contenu
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

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
