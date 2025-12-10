

st.set_page_config(page_title="CoinAfrique Scraper", page_icon="🐾", layout="wide")

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
    .form-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .iframe-container {
        border: 2px solid #2E86AB;
        border-radius: 10px;
        padding: 10px;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>CoinAfrique Animal Scraper</h1>", unsafe_allow_html=True)

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
                status_text.text(f"No listings found on page {page}. Stopping scrape.")
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
            time.sleep(1)
            
        except Exception as e:
            status_text.error(f"Error scraping page {page}: {str(e)}")
            break
    
    progress_bar.empty()
    status_text.empty()
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

def save_to_db(df):
    conn = sqlite3.connect('coinafrique_data.db')
    df.to_sql('scraped_data', conn, if_exists='append', index=False)
    conn.close()

def load_from_db():
    conn = sqlite3.connect('coinafrique_data.db')
    df = pd.read_sql_query("SELECT * FROM scraped_data", conn)
    conn.close()
    return df

def clean_data(df):
    df_clean = df.copy()
    df_clean['price'] = pd.to_numeric(df_clean['price'], errors='coerce')
    df_clean = df_clean.dropna(subset=['price'])
    df_clean = df_clean[df_clean['price'] > 0]
    return df_clean

def load_csv_data(filename):
    try:
        df = pd.read_csv(f'data/{filename}')
        return df
    except FileNotFoundError:
        st.error(f"File not found: data/{filename}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return pd.DataFrame()

init_db()

st.sidebar.title("Navigation")
page = st.sidebar.radio("Choose a page:", 
                        ["Scraper", "Dashboard", "Download Data", "Evaluation"])

CATEGORIES = {
    "Dogs": "https://sn.coinafrique.com/categorie/chiens",
    "Sheep": "https://sn.coinafrique.com/categorie/moutons",
    "Chickens, Rabbits & Pigeons": "https://sn.coinafrique.com/categorie/poules-lapins-et-pigeons",
    "Other Animals": "https://sn.coinafrique.com/categorie/autres-animaux"
}

CSV_FILES = {
    "Other Animals Data": "autres_animaux_data.csv",
    "Dogs Data": "chiens.data.csv",
    "Chickens Rabbits Pigeons Data": "lapin_poule_pigeon_data.csv",
    "Sheep Data": "moutons_data.csv"
}

if page == "Scraper":
    st.header("Scrape Data")
    st.markdown("Select a category and the number of pages to scrape.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_category = st.selectbox("Category:", list(CATEGORIES.keys()))
    
    with col2:
        num_pages = st.number_input("Number of pages:", min_value=1, max_value=50, value=5)
    
    if st.button("Start Scraping"):
        with st.spinner("Scraping in progress..."):
            df = scrape_all_pages(CATEGORIES[selected_category], selected_category, num_pages)
            
            if not df.empty:
                st.success(f"{len(df)} listings scraped successfully!")
                save_to_db(df)
                st.dataframe(df.head(10))
                st.info(f"Data saved to SQLite database")
            else:
                st.warning("No data found.")

elif page == "Dashboard":
    st.header("Data Dashboard")
    
    df = load_from_db()
    
    if df.empty:
        st.warning("No data available. Please scrape data first.")
    else:
        df_clean = clean_data(df)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Listings", len(df_clean))
        with col2:
            st.metric("Average Price", f"{df_clean['price'].mean():,.0f} CFA")
        with col3:
            st.metric("Minimum Price", f"{df_clean['price'].min():,.0f} CFA")
        with col4:
            st.metric("Maximum Price", f"{df_clean['price'].max():,.0f} CFA")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.box(df_clean, x='category', y='price', 
                         title="Price Distribution by Category",
                         labels={'price': 'Price (CFA)', 'category': 'Category'})
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            cat_counts = df_clean['category'].value_counts()
            fig2 = px.pie(values=cat_counts.values, names=cat_counts.index,
                         title="Listings Distribution by Category")
            st.plotly_chart(fig2, use_container_width=True)
        
        city_counts = df_clean['adresse'].value_counts().head(10)
        fig3 = px.bar(x=city_counts.index, y=city_counts.values,
                     title="Top 10 Cities with Most Listings",
                     labels={'x': 'City', 'y': 'Number of Listings'})
        st.plotly_chart(fig3, use_container_width=True)
        
        st.subheader("Cleaned Data Preview")
        st.dataframe(df_clean, use_container_width=True)

elif page == "Download Data":
    st.header("Download Data")
    st.markdown("View and download pre-scraped CSV data files.")
    
    if 'selected_csv' not in st.session_state:
        st.session_state.selected_csv = None
    
    st.markdown("### Select a dataset to view:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Other Animals Data", use_container_width=True):
            st.session_state.selected_csv = "Other Animals Data"
        
        if st.button("Chickens Rabbits Pigeons Data", use_container_width=True):
            st.session_state.selected_csv = "Chickens Rabbits Pigeons Data"
    with col2:
        if st.button("Dogs Data", use_container_width=True):
            st.session_state.selected_csv = "Dogs Data"
        
        if st.button("Sheep Data", use_container_width=True):
            st.session_state.selected_csv = "Sheep Data"
    
    if st.session_state.selected_csv:
        st.markdown("---")
        st.subheader(f"Viewing: {st.session_state.selected_csv}")
        
        df = load_csv_data(CSV_FILES[st.session_state.selected_csv])
        
        if not df.empty:
            st.write(f"Data dimension: {df.shape[0]} rows and {df.shape[1]} columns.")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download this CSV",
                data=csv,
                file_name=CSV_FILES[st.session_state.selected_csv],
                mime='text/csv',
                use_container_width=True
            )
    else:
        st.info("Please select a dataset to view by clicking one of the buttons above.")

elif page == "Evaluation":
    st.header("App Evaluation Forms")
    st.markdown("Please provide your feedback using one of the forms below:")
    
    tab1, tab2 = st.tabs(["KoboToolbox Form", "Google Form"])
    
    with tab1:
        st.markdown("""
        <div class='form-card'>
            <h3>KoboToolbox Evaluation Form</h3>
            <p>Complete our evaluation survey via KoboToolbox platform.</p>
        </div>
        """, unsafe_allow_html=True)
        
        kobotoolbox_url = "https://ee.kobotoolbox.org/x/GKAR6J8r"
        
        st.markdown(f"""
        <div class='iframe-container'>
            <iframe src="{kobotoolbox_url}" width="100%" height="800" frameborder="0" marginheight="0" marginwidth="0">
                Loading form...
            </iframe>
        </div>
        """, unsafe_allow_html=True)
    
    with tab2:
        st.markdown("""
        <div class='form-card'>
            <h3>Google Forms Evaluation</h3>
            <p>Complete our evaluation survey via Google Forms.</p>
        </div>
        """, unsafe_allow_html=True)
        
        google_form_url = "https://docs.google.com/forms/d/e/1FAIpQLScOzEb9-oQIWjcMbC4CUgp5qP7ND4zvRWGo734Yjspd-W8nVw/viewform?usp=header"
        
        if "viewform" in google_form_url:
            embed_url = google_form_url.replace("viewform", "viewform?embedded=true")
        else:
            embed_url = google_form_url
        
        st.markdown(f"""
        <div class='iframe-container'>
            <iframe src="{embed_url}" width="100%" height="800" frameborder="0" marginheight="0" marginwidth="0">
                Loading form...
            </iframe>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.success("Thank you for taking the time to evaluate our application!")

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>Developed with Streamlit | Data from <a href='https://sn.coinafrique.com'>CoinAfrique</a></p>
</div>
""", unsafe_allow_html=True)







