import feedparser
from ics import Calendar, Event
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

# Set timezones
local_tz = pytz.timezone("America/New_York")
boston_tz = ZoneInfo("America/New_York")

# --- 1. AllEvents Feed ---
def get_allevents():
    driver = webdriver.Chrome()
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

# --- 2. Eventbrite Feed ---
def get_eventbrite():
    urls = [
        "https://www.eventbrite.com/d/united-states--massachusetts/hyde-park/",
        "https://www.eventbrite.com/d/united-states--massachusetts/hyde-park/?page=2"
    ]
    driver = webdriver.Chrome()
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

# --- 3. BPL RSS Feed ---
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
            events.append({"title": title, "date": dt.strftime("%Y-%m-%d %H:%M"), "location": location, "url": url})
        except Exception:
            continue
    return events

# --- 4. Historical Society ---
def get_historical_events():
    url = 'https://www.hydeparkhistoricalsociety.org/news/'
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    current_date = datetime.now(boston_tz)
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
        return {"title": title, "date": event_date.strftime("%Y-%m-%d %H:%M"), "location": "Hyde Park Historical Society", "url": url}

    for e in entries:
        ev = extract(e)
        if ev:
            events.append(ev)
    return events

# --- Create ICS calendar ---
def create_ics(events, output_file="hydepark_events_combined.ics"):
    calendar = Calendar()
    calendar.extra.append("X-WR-TIMEZONE:America/New_York")
    for e in events:
        try:
            event = Event()
            event.name = e["title"]
            event.begin = local_tz.localize(datetime.strptime(e["date"], "%Y-%m-%d %H:%M"))
            event.end = event.begin + timedelta(hours=1)
            event.location = e["location"]
            event.description = f'URL: {e.get("url", "")}'
            event.uid = f"{uuid4()}@hydeparkevents"
            calendar.events.add(event)
        except Exception:
            continue
    with open(output_file, "w") as f:
        f.writelines(calendar)
    print(f"✅ ICS file written to: {output_file}")

if __name__ == "__main__":
    all_events = get_allevents() + get_eventbrite() + get_bpl_events() + get_historical_events()
    create_ics(all_events)
