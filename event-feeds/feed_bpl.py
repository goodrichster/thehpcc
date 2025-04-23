import feedparser
from ics import Calendar, Event
from ics.grammar.parse import ContentLine
from datetime import datetime
import pytz
from uuid import uuid4

# Filename is bpl_feedparser.py
# Parse the RSS feed
feed_url = 'https://gateway.bibliocommons.com/v2/libraries/bpl/rss/events?locations=27&cancelled=false'
feed = feedparser.parse(feed_url)

# Set timezone
local_tz = pytz.timezone("America/New_York")

# Create calendar and declare timezone
calendar = Calendar()
calendar.extra.append(ContentLine(name="X-WR-TIMEZONE", value="America/New_York"))

def parse_local_datetime(date_str):
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return local_tz.localize(datetime.strptime(date_str, fmt))
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {date_str}")

# Process all entries
for entry in feed.entries:
    try:
        event = Event()
        

        event.name = entry.title
        # append date in title using mm/dd/yyyy HH:MM format with the key bc_start_date_local
        #  first convert bc_start_date_local to datetime object
        #  then convert to string with strftime
        #  then append to event.name                
        date_str = entry.get('bc_start_date_local')
        new_title = entry.title
        if date_str:
            try:
                new_title_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
                new_title_date_str = new_title_date.strftime('%B %d %I:%M %p')
                new_title += " @BPL "
            except ValueError:
                new_title += ""
        else:
            new_title += " (No date found)"

        event.name = new_title

        print(event.name, new_title_date_str)
    # 
        # Description
        event.description = getattr(entry, 'summary', '')
        # find the image URL from the links key
        #  then append to event.description
        image_url = ""
        for link in entry.links:
            if link.get('type') == 'image/jpeg':
                image_url = link.get('href')
                break
        # if image_url:
        #     event.description += f"\n\nImage: {image_url}"
        # else:    
        #     event.description += ""
        # add an img htmk tag to the description
        # Featured image
        featured_image = featured_image = f'<div class="tribe-events-event-image"><img width="500" height="375" src="{image_url}" class="attachment-full size-full wp-post-image"></div>'


        event.description = featured_image + event.description

        # URL
        # event.url = getattr(entry, 'link', '')
        event.url = entry.link

        # event.description = entry.get("summary", "")
        
        
        event.uid = f"{uuid4()}@bplfeed"

        # Parse and assign local datetime
        start_str = entry.get("bc_start_date_local", "")
        end_str = entry.get("bc_end_date_local", "")
        event.begin = parse_local_datetime(start_str)
        event.end = parse_local_datetime(end_str)

        # Add event
        calendar.events.add(event)
    except Exception as e:
        print(f"Skipped event due to error: {e}")

# Save to .ics file
with open("bpl_feed_calendar.ics", "w") as f:
    f.writelines(calendar)

print(f"✅ Finished: {len(calendar.events)} events written to bpl_feed_calendar.ics")

# upload iCS file to google drive
# https://drive.google.com/file/d/1JOJNPBaKH9T3xoEod9yk8ZW735OxEcfW/view?usp=sharing
# ics file: bpl_feed_calendar.ics

# connect to drive
# from pydrive.auth import GoogleAuth
# from pydrive.drive import GoogleDrive

# gauth = GoogleAuth()
# gauth.LocalWebserverAuth()
# drive = GoogleDrive(gauth)

# # Upload the file
# file = drive.CreateFile({'title': 'bpl_feed_calendar.ics'})
# file.SetContentFile('bpl_feed_calendar.ics')
# file.Upload()

# print(f"File uploaded successfully. File ID: {file['id']}")


# https://drive.google.com/uc?export=download&id=YOUR_FILE_ID
# https://drive.google.com/uc?export=download&id=1JOJNPBaKH9T3xoEod9yk8ZW735OxEcfW