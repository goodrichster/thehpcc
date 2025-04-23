# This script scrapes the Hyde Park Historical Society website for event information.
# It retrieves the previous and next events based on the current date.
# It uses BeautifulSoup for HTML parsing and requests for HTTP requests.
# Filename is hydeparkhistoricalsociety-events.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

# Define Boston timezone
boston_tz = ZoneInfo("America/New_York")

# Localized current time
current_date = datetime.now(boston_tz)

url = 'https://www.hydeparkhistoricalsociety.org/news/'

response = requests.get(url)
response.raise_for_status()

soup = BeautifulSoup(response.text, 'html.parser')

event_entries = soup.find_all('article')


previous_event = None
next_event = None

def extract_event_data(entry):
    try:
        # Extract date
        time_tag = entry.find('time')
        if not time_tag or not time_tag.has_attr('datetime'):
            return None
        event_date = datetime.fromisoformat(time_tag['datetime'])

        # Extract title (try multiple options in case structure varies)
        title_tag = entry.find('h2') or entry.find('h3')
        title = title_tag.get_text(strip=True) if title_tag else 'Untitled Event'

        # Extract description (you may need to adjust this)
        desc_tag = entry.find('p') or entry.find('div')
        description = desc_tag.get_text(strip=True) if desc_tag else 'No description available.'

        return {
            'date': event_date,
            'title': title,
            'description': description
        }
    except Exception as e:
        print(f"Error parsing entry: {e}")
        return None

# Find previous and next events
for entry in event_entries:
    event = extract_event_data(entry)
    if not event:
        continue
    if event['date'] < current_date:
        if not previous_event or event['date'] > previous_event['date']:
            previous_event = event
    elif event['date'] >= current_date:
        if not next_event or event['date'] < next_event['date']:
            next_event = event

# Print results
if previous_event:
    print("\nPrevious Event:")
    print(f"Title: {previous_event['title']}")
    print(f"Date: {previous_event['date'].strftime('%B %d, %Y')}")
    print(f"Description: {previous_event['description']}")
else:
    print("No previous events found.")

if next_event:
    print("\nNext Event:")
    print(f"Title: {next_event['title']}")
    print(f"Date: {next_event['date'].strftime('%B %d, %Y')}")
    print(f"Description: {next_event['description']}")
else:
    print("No upcoming events found.")
