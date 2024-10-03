import os
import requests
import mysql.connector
from playwright.sync_api import sync_playwright
import json

# For countries
def scrape_data():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Navigate to the Angular-based website
        page.goto("https://www.wikiart.org/en/artists-by-nation")

        try:
            # Wait for the dynamic content to load (adjust selector based on your site)
            page.wait_for_selector("ul.dictionaries-list", timeout=60000)  # Increased timeout to 60 seconds

            # Handle pagination and scrape data
            data = []
            while True:
                # Extract data from the current page (adjust the selector based on the data you need)
                items = page.query_selector_all("li.dottedItem")
                for item in items:
                    title = item.query_selector("a").inner_text()
                    data.append({
                        "title": title.split()[0].lower(),
                        "link": item.query_selector("a").get_attribute("href")
                    })

                # Check if there is a next page button and click it
                next_button = page.query_selector("a.next")
                if next_button:
                    next_button.click()
                    page.wait_for_selector("li.dottedItem", timeout=60000)  # Wait for items to load on the next page
                else:
                    break

        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            browser.close()

        return data

# store countries in mysql
def store_data_in_mysql(data):
    # Connect to the MySQL database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS country (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255),
            link VARCHAR(255)
        )
    """)

    cursor.execute("TRUNCATE TABLE country")

    # Insert data into the table
    for item in data:
        cursor.execute("""
            INSERT INTO country (title, link)
            VALUES (%s, %s)
        """, (item["title"], item["link"]))

    # Commit the transaction
    conn.commit()

    # Close the connection
    cursor.close()
    conn.close()

# for country artists
def scrapCountryArtist():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Navigate to the Angular-based website
        base_url = "https://www.wikiart.org"
        countries = fetch_countries()
        # print(countries)
        for country in countries:
            id = country[0]
            country_name = country[1]
            country_link = country[2]
            if country_link == "/en/artists-by-nation/albanian":
                page.goto(base_url + country_link)
        

                # Wait for the dynamic content to load (adjust selector based on your site)
                page.wait_for_selector("ul.wiki-artistgallery-container")

                # Handle pagination and scrape data
                data = []
                while True:

                    meta_elements = page.query_selector_all("meta")
                    meta_tags = {}
                    for meta in meta_elements:
                        name = meta.get_attribute("name")
                        property = meta.get_attribute("property")
                        content = meta.get_attribute("content")
                        if name:
                            meta_tags[name] = content
                        elif property:
                            meta_tags[property] = content

                    # Extract data from the current page (adjust the selector based on the data you need)
                    items = page.query_selector_all("li.ng-scope")
                    for item in items:
                        title = item.query_selector("a.ng-binding").inner_text()
                        year = item.query_selector("div.artist-short-info").inner_text()
                        image = item.query_selector("img").get_attribute("src")
                        artworks = item.query_selector("div.works-count").inner_text()
                        link = item.query_selector("a.image-wrapper").get_attribute("href")
                        
                        # Create directory if it doesn't exist
                        directory = "images/profiles"
                        if not os.path.exists(directory):
                            os.makedirs(directory)

                        # Download and save the image
                        image_name = os.path.join(directory, os.path.basename(image))
                        download_image(image, image_name)

                        data.append({
                            "country_id": id,
                            "title": title,
                            "year": year,
                            "link": link,
                            "image": image_name,
                            "artworks": artworks,
                            "meta_tags": meta_tags  # Add meta_tags to the data dictionary
                        })

                    # Check if a "Next" button exists and is enabled, then click to go to the next page
                    next_button = page.query_selector("a.masonry-load-more-button")
                    if next_button and next_button.is_visible():
                        # print(next_button)
                        next_button.click()
                        page.wait_for_timeout(1000)  # Wait for the next page to load
                    else:
                        break
                # print(data)    
                

                browser.close()
                return data   
        return []  

#store country artists in mysql  
def store_country_artist_data_in_mysql(data):
    # print(data[0]["meta_tags"])
    # return []
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS country_artists (
            id INT AUTO_INCREMENT PRIMARY KEY,
            country_id INT,
            title VARCHAR(255),
            year VARCHAR(255),
            link VARCHAR(255),
            image_path VARCHAR(255),
            artworks VARCHAR(255)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS country_artists_metadata (
            id INT AUTO_INCREMENT PRIMARY KEY,
            country_id INT,
            meta_tags JSON
        )
    """)

    cursor.execute("TRUNCATE TABLE country_artists")
    cursor.execute("TRUNCATE TABLE country_artists_metadata")



    # Insert data into the table
    for item in data:
        cursor.execute("""
            INSERT INTO country_artists (country_id,title, year, image_path, artworks, link)
            VALUES (%s,%s, %s, %s, %s, %s)
        """, (item["country_id"],item["title"], item["year"], item["image"], item["artworks"], item["link"]))

    cursor.execute("""
            INSERT INTO country_artists_metadata (country_id, meta_tags)
            VALUES (%s, %s)
        """, (data[0]["country_id"], json.dumps(data[0]["meta_tags"])))  

    # Commit the transaction
    conn.commit()

    # Close the connection
    cursor.close()
    conn.close()                
    
# Function to fetch country data from MySQL
def fetch_countries():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM country")
    countries = cursor.fetchall()
    cursor.close()
    conn.close()
    return countries

# store artist info
def scrap_artist_data():
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # page.set_viewport_size({"width": 1280, "height": 800})

        # previous_height = page.evaluate("document.body.scrollHeight")

        # Navigate to the Angular-based website
        base_url = "https://www.wikiart.org"
        artists = fetch_country_artist_data()
        data = []

        for artist in artists:
            artist_id = artist[0]
            link = artist[1]
            image_path = artist[2]
            title = artist[3]
            try:
                page.goto(base_url + link)
                # print(base_url + link)
                # return []
                # Wait for the dynamic content to load (adjust selector based on your site)
                # page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                # page.wait_for_timeout(1000)

                page.wait_for_selector("div.wiki-layout-artist-info")
                # return []

                # Handle pagination and scrape data
                while True:
                   # Use wait_for_timeout to pause for images to load (non-blocking alternative to time.sleep)
                    # page.wait_for_timeout(1000)  # Wait for 1 second

                    # Get the updated scroll height after scrolling
                    # new_height = page.evaluate("document.body.scrollHeight")
                    
                    # print("inside while")

                    meta_elements = page.query_selector_all("meta")
                    meta_tags = {}
                    span_tags = {}
                    for meta in meta_elements:
                        name = meta.get_attribute("name")
                        property = meta.get_attribute("property")
                        content = meta.get_attribute("content")
                        if name:
                            meta_tags[name] = content
                        elif property:
                            meta_tags[property] = content
                              
                    # print(meta_tags)    
                    # return []        

                    # Extract data from the current page (adjust the selector based on the data you need)
                    items = page.query_selector_all("li.dictionary-values")
                   # Find all <span> tags within the <li> item
                    for item in items:
                        type_title = item.query_selector("s").inner_text().rstrip(':').lower()
                        nationality = ""
                        if (type_title != 'influenced by' and type_title != 'influenced on'):
                            spans = item.query_selector_all("span")
                            for span in spans:
                                # Extract the inner text from each <span> tag
                                nationality += span.inner_text()
                            span_tags[type_title] = nationality   
                        else:
                            links = item.query_selector_all("a[target='_self']")
                            if links:
                                for link in links:
                                    nationality += link.inner_text()
                                span_tags[type_title] = nationality+','

                    birth_date_span = page.query_selector('span[itemprop="birthDate"]').inner_text()
                    death_date_span_element = page.query_selector('span[itemprop="deathDate"]')
                    if death_date_span_element:
                        death_date_span = death_date_span_element.inner_text()
                    else:
                       death_date_span = ""     
                    article = page.query_selector('div.wiki-layout-artist-info-wrapper').inner_text()
                    links = page.query_selector_all('li.truncated-link')
                    if links:
                        for link in links:
                            type_title = link.query_selector("s").inner_text().rstrip(':').lower()
                            # print(type_title)
                            span_tags[type_title] = link.query_selector('span').inner_text()

                    items = page.query_selector_all("li.ng-scope")
                    artworks = []
                    for item in items:
                        title = item.query_selector("a.artwork-name").inner_text()
                        name = item.query_selector("a.artist-name").inner_text()
                        image = item.query_selector("img").get_attribute("src")
                        # print(image)
                        # return []
                        link = item.query_selector("a.artwork-name").get_attribute("href")
                        year_element = item.query_selector("span.artwork-year")
                        if year_element:
                            year = year_element.inner_text()
                        else:
                            year = ""
                        
                        # Create directory if it doesn't exist
                        directory = "images/"+title
                        if not os.path.exists(directory):
                            os.makedirs(directory)

                        # Download and save the image
                        image_name = os.path.join(directory, os.path.basename(image))
                        download_image(image, image_name)

                        artworks.append({
                            "title": title,
                            "name": name,
                            "image": image_name,
                            "link": link,
                            "year": year
                        })   

                    data.append({
                        "artist_id": artist_id,
                        "meta_tags": meta_tags,
                        "nationality": span_tags['nationality'].rstrip(','),
                        "art_movement": span_tags['art movement'].rstrip(','),
                        "Field": span_tags['field'].rstrip(','),
                        "influenced_on": span_tags.get('influenced on', '').rstrip(',') if span_tags.get('influenced on') else '',
                        "influenced_by": span_tags.get('influenced by', '').rstrip(',') if span_tags.get('influenced by') else '',
                        "wikipedia": span_tags.get('wikipedia', ''),
                        "official site": span_tags.get('official site', ''),
                        "description": article.rstrip('\n\nMore ...'),
                        "birth_date": birth_date_span,
                        "death_date": death_date_span,
                        "link": artist[1],
                        "image_path": artist[2],
                        "title": artist[3],
                        "artworks": artworks
                    })
                     # Check if a "Next" button exists and is enabled, then click to go to the next page
                    # next_button = page.query_selector("main.btn-view-all")
                    # if next_button and next_button.is_visible():
                    # #     # print(next_button)
                    #     next_button.click()
                    #     page.wait_for_timeout(1000)  # Wait for the next page to load
                    #     page.wait_for_selector("div.artist-menu-block-wrapper")
                    # else:
                    #     break
                    break
            except Exception as e:
                print(f"Error navigating to : {e}") 
        browser.close()
        # print(data)       

        return data       


    # return artist_data

def get_image_link(title,link):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        base_url = "https://www.wikiart.org"
        data = []
        page.goto(base_url + link)
        page.wait_for_selector("div.wiki-layout-artist-info")
       
        # Handle pagination and scrape data
        while True:
            # print("inside while")

            meta_elements = page.query_selector_all("meta")
            meta_tags = {}
            for meta in meta_elements:
                name = meta.get_attribute("name")
                property = meta.get_attribute("property")
                content = meta.get_attribute("content")
                if name:
                    meta_tags[name] = content
                elif property:
                    meta_tags[property] = content
            break; 

        image_url = page.query_selector('img[itemprop="image"]').get_attribute("src")
        local_directory = "images/"+title
        if not os.path.exists(local_directory):
            os.makedirs(local_directory)
            
        image_filename = os.path.join(local_directory, os.path.basename(image_url))
        browser.close()        
    return image_filename    

# store artist data in mysql
def store_artist_data_in_mysql(artist_data):
    # print('eww')
    # print(artist_data[1])
    # return []
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS artist_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            counry_artist_id INT,
            meta_tags JSON,
            nationality VARCHAR(255) NULL,
            art_movement VARCHAR(255) NULL,
            field VARCHAR(255) NULL,
            influenced_on VARCHAR(255) NULL,
            influenced_by VARCHAR(255) NULL,
            wikipedia VARCHAR(255) NULL,
            official_site VARCHAR(255) NULL,
            description TEXT NULL,
            birth_date VARCHAR(255) NULL,
            death_date VARCHAR(255) NULL,
            link VARCHAR(255) NULL,
            image_path VARCHAR(255) NULL,
            title VARCHAR(255) NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS arts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            artist_id INT,
            title VARCHAR(255),
            name VARCHAR(255),
            image VARCHAR(255),
            link VARCHAR(255),
            year VARCHAR(255)
        )
    """)

    cursor.execute("TRUNCATE TABLE artist_data")
    cursor.execute("TRUNCATE TABLE arts")

    max_id = fetch_max_country_artist_id() + 1

    insert_query = """
        INSERT INTO artist_data (
            counry_artist_id, meta_tags, nationality, art_movement, field,
            influenced_on, influenced_by, wikipedia, official_site,
            description, birth_date, death_date, link, image_path, title
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    for item in artist_data:
        cursor.execute(insert_query, (
            item["artist_id"], json.dumps(item["meta_tags"]), item["nationality"],
            item["art_movement"], item["Field"], item["influenced_on"],
            item["influenced_by"], item["wikipedia"], item["official site"],
            item["description"], item["birth_date"], item["death_date"],
            item["link"], item["image_path"], item["title"]
        ))

        for artwork in item["artworks"]:
            cursor.execute("""
                INSERT INTO arts (artist_id, title, name, image, link, year)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (max_id, artwork["title"], artwork["name"], artwork["image"], artwork["link"], artwork["year"]))
        max_id += 1    

    conn.commit()
    cursor.close()
    conn.close()
    return []   

# Function to fetch the maximum id from the country_artists table
def fetch_max_country_artist_id():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT max(id) FROM artist_data")
    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return result if result is not None else 0

# Function to fetch country artist data from MySQL
def fetch_country_artist_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id,link,image_path,title FROM country_artists")
    country_artists = cursor.fetchall()
    cursor.close()
    conn.close()
    return country_artists 

# Function to store art information
def store_art_info():
    arts = fetch_arts_data()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        base_url = "https://www.wikiart.org"
        data = []
        for art in arts:
            artist_id = art[0]
            name = art[1]
            title = art[2]
            link = art[3]
            art_id = art[4]
            page.goto(base_url + link)
            # print(base_url + link)
            # return []
            # Wait for the dynamic content to load (adjust selector based on your site)
            page.wait_for_selector("div.wiki-layout-artist-info")
            # return []

            # Handle pagination and scrape data
            while True:
                # print("inside while")

                meta_elements = page.query_selector_all("meta")
                meta_tags = {}
                for meta in meta_elements:
                    name = meta.get_attribute("name")
                    property = meta.get_attribute("property")
                    content = meta.get_attribute("content")
                    if name:
                        meta_tags[name] = content
                    elif property:
                        meta_tags[property] = content
                break; 

            image_url = page.query_selector('img[itemprop="image"]').get_attribute("src")
            local_directory = "images/"+title
            if not os.path.exists(local_directory):
                os.makedirs(local_directory)
                
            image_filename = os.path.join(local_directory, os.path.basename(image_url))
            
            # Download and save the image locally
            download_image(image_url, image_filename)
            title = page.query_selector('article h3').inner_text()
            artist_name = page.query_selector('span[itemprop="name"]').inner_text() 

            span_tags = {}

            items = page.query_selector_all("li.dictionary-values")
            # Find all <span> tags within the <li> item
            for item in items:
                type_title = item.query_selector("s").inner_text().rstrip(':').lower()
                nationality = ""
                spans = item.query_selector_all("span")
                for span in spans:
                    # Extract the inner text from each <span> tag
                    nationality += span.inner_text()
                span_tags[type_title] = nationality.rstrip(',')
            added_date =  page.query_selector('.text-info span').inner_text()
            max_resolution = page.query_selector('span.max-resolution').inner_text()

            items = page.query_selector_all('div.tags-cheaps__item')
            tags = []
            for item in items:
                tags.append(item.query_selector('a.tags-cheaps__item__ref').inner_text().replace(" ",""))  # Corrected line         
            tags = ','.join(tags)
            
            data.append({
                "artist_id": artist_id,
                "name": name,
                "title": title,
                "artist_name":artist_name,
                "meta_tags":meta_tags,
                "general_info":span_tags,
                "added_date":added_date,
                "max_resolution":max_resolution,
                "tags":tags,
                "art_id": art_id,
                "image": image_filename
            })
        browser.close()        
    return data

def create_table_artwork():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS artworks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        artist_id INT,
        name VARCHAR(255),
        title VARCHAR(255),
        artist_name VARCHAR(255),
        meta_tags JSON,
        general_info JSON,
        added_date VARCHAR(255),
        max_resolution VARCHAR(255),
        tags VARCHAR(255),
        art_id INT,
        image_url VARCHAR(255)
    );
    """
    
    cursor.execute(create_table_sql)
    conn.commit()
    cursor.close()
    conn.close()

def insert_art_data(art_data_list):

    create_table_artwork()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Truncate the table before inserting new data
    cursor.execute("TRUNCATE TABLE artworks")
    
    insert_sql = """
    INSERT INTO artworks (artist_id, name, title, artist_name, meta_tags, general_info, added_date, max_resolution, tags, art_id, image_url)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    for art_data in art_data_list:
        values = (
            art_data["artist_id"],
            art_data["name"],
            art_data["title"],
            art_data["artist_name"],
            json.dumps(art_data["meta_tags"]),
            json.dumps(art_data["general_info"]),
            art_data["added_date"],
            art_data["max_resolution"],
            art_data["tags"],
            art_data["art_id"],
            art_data["image"]
        )
        cursor.execute(insert_sql, values)
        update_image_url(art_data["art_id"], art_data["image"])
    
    conn.commit()
    cursor.close()
    conn.close()

def update_image_url(artist_id, image_url):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    update_sql = """
    UPDATE arts
    SET image = %s
    WHERE id = %s
    """
    
    values = (image_url, artist_id)
    
    cursor.execute(update_sql, values)
    conn.commit()
    cursor.close()
    conn.close()

def fetch_arts_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT artist_id,name,title,link,id FROM arts")
    arts = cursor.fetchall()
    cursor.close()
    conn.close()
    return arts


# Function to download and save images
def download_image(url, save_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            file.write(response.content)      


def fetch_data():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch countries
    cursor.execute("SELECT * FROM country")
    countries = cursor.fetchall()

    # Fetch country artists
    cursor.execute("SELECT * FROM country_artists")
    country_artists = cursor.fetchall()

    # Fetch country artists metadata
    cursor.execute("SELECT * FROM country_artists_metadata")
    country_artists_metadata = cursor.fetchall()

    # Fetch artist data
    cursor.execute("SELECT * FROM artist_data")
    artist_data = cursor.fetchall()

    # Fetch arts
    cursor.execute("SELECT * FROM arts")
    arts = cursor.fetchall()

    cursor.close()
    conn.close()

    # Organize data into a tree-like structure
    data_tree = {}

    for country in countries:
        country_id = country['id']
        data_tree[country_id] = {
            'country': country,
            'artists': {},
            'metadata': []
        }

    for artist in country_artists:
        country_id = artist['country_id']
        artist_id = artist['id']
        if country_id in data_tree:
            data_tree[country_id]['artists'][artist_id] = {
                'artist': artist,
                'metadata': [],
                'artist_data': [],
                'arts': []
            }

    for metadata in country_artists_metadata:
        country_id = metadata['country_id']
        if country_id in data_tree:
            data_tree[country_id]['metadata'].append(metadata)

    for artist in artist_data:
        artist_id = artist['counry_artist_id']
        for country_id, country_data in data_tree.items():
            if artist_id in country_data['artists']:
                country_data['artists'][artist_id]['artist_data'].append(artist)
    # print(data_tree)            

    for art in arts:
        artist_id = art['artist_id']
        for country_id, country_data in data_tree.items():
            if artist_id in country_data['artists']:
                country_data['artists'][artist_id]['arts'].append(art)

    return data_tree

def save_data_to_json(data, directory, filename):
    # Ensure the directory exists
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Convert data to JSON string
    json_data = json.dumps(data, indent=4)

    # Write JSON string to file
    file_path = os.path.join(directory, filename)
    with open(file_path, 'w') as json_file:
        json_file.write(json_data)

# Common function to establish a database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="scrap"
    )
# Main function
if __name__ == "__main__":
    data = scrape_data()
    print('scrape data')
    store_data_in_mysql(data)
    print('store data')
    artists_data = scrapCountryArtist()
    print('scrap country artist')
    store_country_artist_data_in_mysql(artists_data)
    print('store country artist')
    artist_info = scrap_artist_data()
    print('fetch artist data')
    store_artist_data_in_mysql(artist_info)
    print('store artist data')
    art_info = store_art_info()
    print('art info')
    insert_art_data(art_info)
    print('insert art data')
    # print(art_info)


    # data_tree = fetch_data()
    # print(data_tree)
    # save_data_to_json(data_tree, 'data_directory', 'data_tree.json')
    # print("Data saved to data_directory/data_tree.json")fetch_art_info