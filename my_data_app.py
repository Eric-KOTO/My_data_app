import streamlit as st
import pandas as pd
import sqlite3
from requests import get
from bs4 import BeautifulSoup as bs
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# Configuration de la page
st.set_page_config(page_title="CoinAfrique Scraper", page_icon="🐾", layout="wide")

# Styles CSS personnalisés
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        font-size: 3em;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .stButton>button {
        width: 100%;
        background-color: #2E86AB;
        color: white;
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #1a5276;
    }
</style>
""", unsafe_allow_html=True)

# Titre principal
st.markdown("<h1 class='main-header'>🐾 CoinAfrique Animal Scraper</h1>", unsafe_allow_html=True)

# Configuration de la base de données SQLite
def init_db():
    conn = sqlite3.connect('coinafrique_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS scraped_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  price TEXT,
                  adresse TEXT,
                  image_url TEXT,
                  category TEXT,
                  scrape_date TEXT)''')
    conn.commit()
    conn.close()

# Fonction de scraping améliorée
def scrape_all_pages(base_url, category_name, max_pages=10):
    df_list = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for page in range(1, max_pages + 1):
        status_text.text(f"Scraping page {page}/{max_pages}...")
        url = f"{base_url}?page={page}"
        
        try:
            res = get(url, timeout=10)
            soup = bs(res.content, 'html.parser')
            containers = soup.find_all('div', class_='col s6 m4 l3')
            
            if not containers:
                status_text.text(f"Aucune annonce trouvée à la page {page}. Arrêt du scraping.")
                break
            
            data = []
            for container in containers:
                try:
                    name = container.find('p', 'ad__card-description').text.strip()
                    price = container.find('p', 'ad__card-price').text.replace('CFA', '').replace(' ', '').strip()
                    adresse = container.find('p', 'ad__card-location').span.text.strip()
                    image_url = container.find('img', class_='ad__card-img')['src']
                    
                    data.append({
                        'name': name,
                        'price': price,
                        'adresse': adresse,
                        'image_url': image_url,
                        'category': category_name,
                        'scrape_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                except Exception as e:
                    continue
            
            if data:
                df_list.append(pd.DataFrame(data))
            
            progress_bar.progress(page / max_pages)
            time.sleep(1)  # Pause pour éviter de surcharger le serveur
            
        except Exception as e:
            status_text.error(f"Erreur lors du scraping de la page {page}: {str(e)}")
            break
    
    progress_bar.empty()
    status_text.empty()
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

# Sauvegarder dans la base de données
def save_to_db(df):
    conn = sqlite3.connect('coinafrique_data.db')
    df.to_sql('scraped_data', conn, if_exists='append', index=False)
    conn.close()

# Charger depuis la base de données
def load_from_db():
    conn = sqlite3.connect('coinafrique_data.db')
    df = pd.read_sql_query("SELECT * FROM scraped_data", conn)
    conn.close()
    return df

# Nettoyer les données
def clean_data(df):
    df_clean = df.copy()
    df_clean['price'] = pd.to_numeric(df_clean['price'], errors='coerce')
    df_clean = df_clean.dropna(subset=['price'])
    df_clean = df_clean[df_clean['price'] > 0]
    return df_clean

# Initialisation de la base de données
init_db()

# Sidebar pour la navigation
st.sidebar.title("📋 Navigation")
page = st.sidebar.radio("Choisissez une page:", 
                        ["🔍 Scraper", "📊 Dashboard", "💾 Télécharger les données", "📝 Évaluation"])

# Dictionnaire des catégories
CATEGORIES = {
    "🐕 Chiens": "https://sn.coinafrique.com/categorie/chiens",
    "🐑 Moutons": "https://sn.coinafrique.com/categorie/moutons",
    "🐔 Poules, Lapins et Pigeons": "https://sn.coinafrique.com/categorie/poules-lapins-et-pigeons",
    "🦎 Autres Animaux": "https://sn.coinafrique.com/categorie/autres-animaux"
}

# PAGE 1: SCRAPER
if page == "🔍 Scraper":
    st.header("🔍 Scraper les données")
    st.markdown("Sélectionnez une catégorie et le nombre de pages à scraper.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_category = st.selectbox("Catégorie:", list(CATEGORIES.keys()))
    
    with col2:
        num_pages = st.number_input("Nombre de pages:", min_value=1, max_value=50, value=5)
    
    if st.button("🚀 Lancer le scraping"):
        with st.spinner("Scraping en cours..."):
            df = scrape_all_pages(CATEGORIES[selected_category], selected_category, num_pages)
            
            if not df.empty:
                st.success(f"✅ {len(df)} annonces scrapées avec succès!")
                save_to_db(df)
                st.dataframe(df.head(10))
                st.info(f"📁 Données sauvegardées dans la base de données SQLite")
            else:
                st.warning("Aucune donnée n'a été trouvée.")

# PAGE 2: DASHBOARD
elif page == "📊 Dashboard":
    st.header("📊 Dashboard des données")
    
    df = load_from_db()
    
    if df.empty:
        st.warning("⚠️ Aucune donnée disponible. Veuillez d'abord scraper des données.")
    else:
        df_clean = clean_data(df)
        
        # Métriques principales
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total d'annonces", len(df_clean))
        with col2:
            st.metric("Prix moyen", f"{df_clean['price'].mean():,.0f} CFA")
        with col3:
            st.metric("Prix minimum", f"{df_clean['price'].min():,.0f} CFA")
        with col4:
            st.metric("Prix maximum", f"{df_clean['price'].max():,.0f} CFA")
        
        st.markdown("---")
        
        # Graphiques
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribution des prix par catégorie
            fig1 = px.box(df_clean, x='category', y='price', 
                         title="Distribution des prix par catégorie",
                         labels={'price': 'Prix (CFA)', 'category': 'Catégorie'})
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Nombre d'annonces par catégorie
            cat_counts = df_clean['category'].value_counts()
            fig2 = px.pie(values=cat_counts.values, names=cat_counts.index,
                         title="Répartition des annonces par catégorie")
            st.plotly_chart(fig2, use_container_width=True)
        
        # Annonces par ville
        city_counts = df_clean['adresse'].value_counts().head(10)
        fig3 = px.bar(x=city_counts.index, y=city_counts.values,
                     title="Top 10 des villes avec le plus d'annonces",
                     labels={'x': 'Ville', 'y': 'Nombre d\'annonces'})
        st.plotly_chart(fig3, use_container_width=True)
        
        # Table des données
        st.subheader("📋 Aperçu des données nettoyées")
        st.dataframe(df_clean, use_container_width=True)

# PAGE 3: TÉLÉCHARGER
elif page == "💾 Télécharger les données":
    st.header("💾 Télécharger les données")
    
    df = load_from_db()
    
    if df.empty:
        st.warning("⚠️ Aucune donnée disponible.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Données brutes")
            csv_raw = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Télécharger CSV (brut)",
                data=csv_raw,
                file_name=f'coinafrique_raw_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv'
            )
        
        with col2:
            st.subheader("Données nettoyées")
            df_clean = clean_data(df)
            csv_clean = df_clean.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Télécharger CSV (nettoyé)",
                data=csv_clean,
                file_name=f'coinafrique_clean_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv'
            )
        
        st.info(f"📊 {len(df)} lignes disponibles (brutes) | {len(df_clean)} lignes (nettoyées)")

# PAGE 4: ÉVALUATION
elif page == "📝 Évaluation":
    st.header("📝 Formulaire d'évaluation de l'application")
    
    with st.form("evaluation_form"):
        st.subheader("Donnez votre avis sur l'application")
        
        name = st.text_input("Votre nom (optionnel)")
        rating = st.slider("Note globale", 1, 5, 3)
        ease_of_use = st.select_slider("Facilité d'utilisation", 
                                        options=["Très difficile", "Difficile", "Moyen", "Facile", "Très facile"])
        features = st.multiselect("Fonctionnalités les plus utiles",
                                  ["Scraping", "Dashboard", "Téléchargement", "Base de données"])
        comments = st.text_area("Commentaires et suggestions")
        
        submitted = st.form_submit_button("Envoyer l'évaluation")
        
        if submitted:
            st.success("✅ Merci pour votre évaluation!")
            st.balloons()
            
            # Sauvegarder l'évaluation dans la base de données
            conn = sqlite3.connect('coinafrique_data.db')
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS evaluations
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT,
                          rating INTEGER,
                          ease_of_use TEXT,
                          features TEXT,
                          comments TEXT,
                          date TEXT)''')
            c.execute("INSERT INTO evaluations VALUES (NULL, ?, ?, ?, ?, ?, ?)",
                     (name, rating, ease_of_use, str(features), comments, 
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>Développé avec ❤️ using Streamlit | Données de <a href='https://sn.coinafrique.com'>CoinAfrique</a></p>
</div>
""", unsafe_allow_html=True)
