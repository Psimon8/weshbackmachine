import streamlit as st
import os
import time
import random
from playwright.sync_api import sync_playwright
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

            return json.loads(response.choices[0].message.content)
        except Exception as e:
            st.error(f"Erreur lors de l'analyse: {str(e)}")
            return None

class GoogleSearchTool:
    def take_screenshot(self, keyword):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )

                page = context.new_page()

                search_params = {
                    'q': keyword,
                    'hl': 'fr',
                    'gl': 'FR',
                    'num': 10
                }
                search_url = f"https://www.google.com/search?{urllib.parse.urlencode(search_params)}"

                page.goto(search_url, wait_until="networkidle")

                # Gérer le bouton des cookies
                try:
                    page.click("#L2AGLb", timeout=5000)
                except:
                    pass

                # Faire défiler la page
                page.evaluate("""
                    window.scrollTo(0, document.body.scrollHeight);
                    new Promise((resolve) => setTimeout(resolve, 2000));
                    window.scrollTo(0, 0);
                """)

                # Attendre que la page soit complètement chargée
                page.wait_for_timeout(2000)

                # Prendre la capture d'écran
                screenshot = page.screenshot(full_page=True)

                context.close()
                browser.close()

                return screenshot

        except Exception as e:
            st.error(f"Erreur lors de la capture d'écran: {str(e)}")
            return None

def create_visualization(analysis_results):
    if not analysis_results:
        return None, None

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
