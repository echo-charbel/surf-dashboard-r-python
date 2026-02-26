import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

import importlib, surf_scrap
importlib.reload(surf_scrap)
from surf_scrap import scrape_surf_report

# Fonction principale pour scraper 
def scrape_surf_report(url, output_csv_path=None):
    """
    Scrape le rapport de surf depuis l'URL donnée et enregistre les données dans un dossier 'data_surf' sous le nom 'data_surf.csv' par défaut.

    Paramètres:
    - url: str - L'URL de la page du rapport de surf à scraper.
    - output_csv_path: str ou None - Le chemin du fichier où sauvegarder les données en CSV. Si None, sauvegarde dans 'data_surf/data_surf.csv' par défaut.

    Retourne:
    - df: pandas.DataFrame - Les données scrappées sous forme de DataFrame pandas.
    """
    # Envoyer une requête HTTP à l'URL
    response = requests.get(url)
    
    # Utiliser BeautifulSoup pour analyser le contenu HTML
    soup = BeautifulSoup(response.content, 'html.parser')

    # Trouver les jours de prévisions
    days = soup.find_all('div', class_='forecast-tab')

    # Liste pour stocker toutes les informations
    data = []

    # Parcourir chaque jour de prévision
    for day in days:
        titre = day.find('b')  # Extraire la balise <b> qui contient le jour
        if titre:  # Vérifier que la balise <b> existe
            day_text = titre.text.strip()

            # Extraire les heures, les vagues et les vents
            hours = day.find_all('div', class_='cell date with-border')
            waves = day.find_all('div', class_='cell large waves with-border')
            winds = day.select('div[class^="wind wind"]')  # Sélecteur partiel pour le vent
            wind_directions = day.find_all('img', alt=lambda alt: 'Orientation vent' in alt)  # Orientation du vent

            # Ajouter les données pour chaque heure dans la journée
            for i in range(len(hours)):
                # Extraire l'heure
                hour = hours[i].text.strip()

                # Extraire la taille des vagues
                wave = waves[i].text.strip()

                # Extraire la vitesse du vent
                wind = winds[i].text.strip()

                # Extraire l'orientation du vent
                wind_direction = wind_directions[i]['alt'].strip()

                # Ajouter les données à la liste
                data.append([day_text, hour, wave, wind, wind_direction])

    # Convertir les données en DataFrame pandas
    df = pd.DataFrame(data, columns=['Day', 'Hour', 'Waves_size', 'Wind_speed', 'Wind_direction'])

    # Si aucun chemin de fichier CSV n'est fourni, enregistrer dans 'data_surf/data_surf.csv'
    if output_csv_path is None:
        # Obtenir le répertoire actuel du script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Définir le chemin du dossier 'data_surf'
        data_surf_dir = os.path.join(current_dir, 'data_surf')
        
        # Créer le dossier 'data_surf' s'il n'existe pas déjà
        if not os.path.exists(data_surf_dir):
            os.makedirs(data_surf_dir)
        
        # Définir le chemin du fichier CSV dans le dossier 'data_surf'
        output_csv_path = os.path.join(data_surf_dir, 'data_surf.csv')  # Assurez-vous que l'extension est .csv

    # Enregistrer les données dans le fichier CSV
    df.to_csv(output_csv_path, index=False)
    print(f"Les données ont été sauvegardées avec succès dans {output_csv_path}")

    # Retourner le DataFrame
    return df 

# Exemple d'utilisation de la fonction scrape_surf_report
df = scrape_surf_report(
    "https://www.surf-report.com/meteo-surf/lacanau-s1043.html",
    "../data/lacanau.csv"
)
df
