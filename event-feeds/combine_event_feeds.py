import feedparser  # May be flagged by Pylance if the module isn't in your current interpreter
from ics import Calendar, Event
from ics.grammar.parse import Container, ContentLine
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import pytz
import requests
from uuid import uuid4
from zoneinfo import ZoneInfo
import time
from selenium.webdriver.chrome.options import Options
from dateutil import parser as date_parser  # Robust natural date parsing
import re

# Set timezones
local_tz = pytz.timezone("America/New_York")
boston_tz = ZoneInfo("America/New_York")

# Chrome driver options (safe config without user-data-dir)
def get_chrome_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--remote-debugging-port=9222')
    return webdriver.Chrome(options=options)

# Clean and parse various fuzzy or irregular date formats
def clean_and_parse_date(raw_date):
    if not raw_date or raw_date.strip().lower() in ["sales end soon", "going fast", "just added", "almost full"]:
        raise ValueError(f"Could not parse date: {raw_date}")
    cleaned = re.sub(r"\s*•.*", "", raw_date)              # Remove trailing '• ...'
    cleaned = re.sub(r"\s*\+.*", "", cleaned)              # Remove trailing '+ N more'
    cleaned = cleaned.strip()
    try:
        return date_parser.parse(cleaned, fuzzy=True)
    except Exception:
        raise ValueError(f"Could not parse date: {raw_date}")

# --- AllEvents Feed ---
def get_allevents():
    driver = get_chrome_driver()
    driver.get("https://allevents.in/hyde%20park-ma?ref=cityselect")
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.event-card"))
    )
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    event_blocks = soup.select("li.event-card")
    events = []
    for block in event_blocks:
        title_tag = block.select_one("div.title h3")
        location_tag = block.select_one("div.subtitle")
        date_tag = block.select_one("div.date")
        title = title_tag.get_text(strip=True) if title_tag else "Untitled"
        location = location_tag.get_text(strip=True) if location_tag else "Location not found"
        date = date_tag.get_text(strip=True) if date_tag else "Date not found"
        events.append({"title": title, "location": location, "date": date})
    return events

# --- Eventbrite Feed ---
def get_eventbrite():
    urls = [
        "https://www.eventbrite.com/d/united-states--massachusetts/hyde-park/",
        "https://www.eventbrite.com/d/united-states--massachusetts/hyde-park/?page=2"
    ]
    driver = get_chrome_driver()
    events = []

    for url in urls:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.event-card"))
        )
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        event_cards = soup.select("div.event-card")

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
            events.append({"title": title, "date": date, "location": location, "url": url})
    driver.quit()
    return events

# --- BPL RSS Feed ---
def get_bpl_events():
    feed_url = 'https://gateway.bibliocommons.com/v2/libraries/bpl/rss/events?locations=27&cancelled=false'
    feed = feedparser.parse(feed_url)
    events = []

    def parse_local_datetime(date_str):
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
            try:
                return local_tz.localize(datetime.strptime(date_str, fmt))
            except ValueError:
                continue
        return None

    for entry in feed.entries:
        try:
            title = entry.title
            start_str = entry.get("bc_start_date_local", "")
            dt = parse_local_datetime(start_str)
            if not dt:
                continue
            location = "Boston Public Library, Hyde Park"
            url = entry.link
            description = getattr(entry, "summary", "")
            events.append({"title": title, "date": dt.strftime("%Y-%m-%d %H:%M"), "location": location, "url": url, "description": description})
        except Exception:
            continue
    return events

# --- Historical Society Feed ---
def get_historical_events():
    url = 'https://www.hydeparkhistoricalsociety.org/news/'
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    entries = soup.find_all('article')

    events = []

    def extract(entry):
        time_tag = entry.find('time')
        if not time_tag or not time_tag.has_attr('datetime'):
            return None
        event_date = datetime.fromisoformat(time_tag['datetime']).astimezone(boston_tz)
        title_tag = entry.find('h2') or entry.find('h3')
        title = title_tag.get_text(strip=True) if title_tag else 'Untitled Event'
        desc_tag = entry.find('p') or entry.find('div')
        description = desc_tag.get_text(strip=True) if desc_tag else ''
        return {"title": title, "date": event_date.strftime("%Y-%m-%d %H:%M"), "location": "Hyde Park Historical Society", "url": url, "description": description}

    for e in entries:
        ev = extract(e)
        if ev:
            events.append(ev)
    return events

# --- Create ICS calendar ---
def create_ics(events, output_file="hydepark_events_combined.ics"):
    calendar = Calendar()
    calendar.extra = Container(name="X-WR-TIMEZONE")
    calendar.extra.append(ContentLine(name="X-WR-TIMEZONE", value="America/New_York"))

    for e in events:
        try:
            parsed = clean_and_parse_date(e["date"])
            event = Event()
            event.name = e["title"]
            event.begin = parsed.replace(tzinfo=local_tz)
            event.end = event.begin + timedelta(hours=1)
            event.location = e["location"]
            event.description = e.get("description", f'URL: {e.get("url", "")}')
            event.uid = f"{uuid4()}@hydeparkevents"
            calendar.events.add(event)
        except Exception as ex:
            print(f"❌ Failed to add event: {e['title']}, error: {ex}")
            continue

    with open(output_file, "w") as f:
        f.writelines(calendar.serialize_iter())
    print(f"✅ ICS file written to: {output_file}")

if __name__ == "__main__":
    print("🚀 Starting event feed combination...")
    all_events = get_allevents() + get_eventbrite() + get_bpl_events() + get_historical_events()
    create_ics(all_events)
    print("✅ Event feed combination completed.")
