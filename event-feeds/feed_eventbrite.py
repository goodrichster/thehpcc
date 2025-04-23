from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# URLs to scrape
urls = [
    "https://www.eventbrite.com/d/united-states--massachusetts/hyde-park/",
    "https://www.eventbrite.com/d/united-states--massachusetts/hyde-park/?page=2"
]

# Start browser
driver = webdriver.Chrome()
events = []

for url in urls:
    print(f"Loading: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.event-card"))
        )
        print("✅ Event cards loaded.")
    except Exception as e:
        print("❌ Event cards failed to load:", e)
        continue

    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    event_cards = soup.select("div.event-card")
    print(f"✅ Found {len(event_cards)} events on this page.")

    for card in event_cards:
        details = card.select_one("section.event-card-details")
        link_tag = card.select_one("a.event-card-link")

        if not details or not link_tag:
            continue

        title_tag = details.find("h3")
        p_tags = details.find_all("p")

        title = title_tag.get_text(strip=True) if title_tag else "Untitled"
        date = p_tags[0].get_text(strip=True) if len(p_tags) > 0 else "Date not found"
        location = p_tags[1].get_text(strip=True) if len(p_tags) > 1 else "Location not found"
        url = link_tag['href'] if link_tag.has_attr('href') else "No URL"

        events.append({
            "title": title,
            "date": date,
            "location": location,
            "url": url
        })

driver.quit()

# ✅ Deduplicate by (title + date)
unique = {}
for event in events:
    key = (event['title'], event['date'])
    if key not in unique:
        unique[key] = event

deduped_events = list(unique.values())

# ✅ Output CSV-style lines
print(f"\n🎉 Collected {len(deduped_events)} unique events from Eventbrite:\n")
print('"Title","Date","Location","URL"')

for event in deduped_events:
    # Escape quotes inside fields
    title = event['title'].replace('"', '""')
    date = event['date'].replace('"', '""')
    location = event['location'].replace('"', '""')
    url = event['url'].replace('"', '""')

    print(f'"{title}","{date}","{location}","{url}"')
