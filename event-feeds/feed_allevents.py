from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

#Filemame: all_events_feeder_HP.py
# Start a visible Chrome browser
driver = webdriver.Chrome()

# Go to the Hyde Park events page
url = "https://allevents.in/hyde%20park-ma?ref=cityselect"
driver.get(url)

# Wait until the event cards are present
try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.event-card"))
    )
    print("✅ Event cards loaded.")
except Exception as e:
    print("❌ Failed to load event cards:", e)
    driver.quit()
    exit()

# Optional: give JS images or lazy-loads more time
time.sleep(3)

# Parse the page content
soup = BeautifulSoup(driver.page_source, "html.parser")
driver.quit()

# Get all event blocks
event_blocks = soup.select("li.event-card")
print(f"✅ Found {len(event_blocks)} events.\n")

# Extract info
events = []
for block in event_blocks:
    title_tag = block.select_one("div.title h3")
    location_tag = block.select_one("div.subtitle")
    date_tag = block.select_one("div.date")

    title = title_tag.get_text(strip=True) if title_tag else "Untitled"
    location = location_tag.get_text(strip=True) if location_tag else "Location not found"
    date = date_tag.get_text(strip=True) if date_tag else "Date not found"

    events.append({
        "title": title,
        "location": location,
        "date": date
    })

# Print the events
for event in events:
    print(f"{event['title']} — {event['date']} @ {event['location']}")
