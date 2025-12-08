# University Price Check System

This application scrapes tuition prices from private universities in Turkey using Scrapy web scraping framework and provides various filtering options including scholarships and preference discounts.

## Features

- Scrape tuition prices from 76 private universities using Scrapy
- Search by university name or department
- Calculate 50% scholarship prices
- Apply preference discounts (5%-60% depending on university)
- View score type, quota, minimum score, and ranking information
- Export to Excel and PDF formats
- Push notification support via ntfy.sh
- MongoDB database for data persistence

## Prerequisites

* Python 3.8 or higher
* pip (Python package manager)
* MongoDB (local or cloud)

---

## Step 1: MongoDB Setup

The application stores data in MongoDB. You can use one of the following options:

### Option A: MongoDB Atlas (Cloud - Recommended)

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free account
3. Create a new cluster (select Free Tier)
4. Go to "Database Access" and create a user (username/password)
5. Go to "Network Access" and add your IP address (or use 0.0.0.0/0 to allow all IPs)
6. Click "Connect" button and select "Connect your application"
7. Copy the connection string:
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/
   ```

### Option B: Local MongoDB

1. Download [MongoDB Community Server](https://www.mongodb.com/try/download/community)
2. Complete the installation
3. Make sure MongoDB service is running:
   ```bash
   # Windows
   net start MongoDB
   
   # Linux/Mac
   sudo systemctl start mongod
   ```
4. Connection string: `mongodb://localhost:27017/`

---

## Step 2: Project Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd Python-Project-1
```

2. Create and activate a virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Step 3: Environment Variables

You need to set the following environment variables for the application to work:

### MongoDB Connection

```bash
# Windows PowerShell
$env:MONGO_URI = "mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/"

# Windows CMD
set MONGO_URI=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/

# Linux/Mac
export MONGO_URI="mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/"
```

> **Note:** If using local MongoDB: `mongodb://localhost:27017/`

### Push Notifications (Optional)

To receive phone notifications when scraping is complete:

1. Download [ntfy.sh](https://ntfy.sh) app on your phone
2. Create a unique topic name in the app (e.g., `my-university-prices`)
3. Set it as an environment variable:

```bash
# Windows PowerShell
$env:NOTIFY_TOPIC = "my-university-prices"

# Windows CMD
set NOTIFY_TOPIC=my-university-prices

# Linux/Mac
export NOTIFY_TOPIC="my-university-prices"
```

---

## Step 4: Populate Database (First Run)

On first use, the database is empty. You need to scrape university data first:

```bash
# Scrape all universities (76 universities, ~2-3 minutes)
python main.py --scrape
```

This command:
- Fetches tuition prices from 76 private universities
- Saves data to MongoDB
- Sends a phone notification if notification topic is set

---

## Usage

### Basic Commands

```bash
# Show help message
python main.py --help

# List universities in database
python main.py --list

# Export all data to Excel/PDF
python main.py --export

# Show notifications
python main.py --show-notifications
```

### Scraping Options

```bash
# Scrape all universities
python main.py --scrape

# Set delay between requests (in seconds)
python main.py --scrape --scrape-delay 1.0

# Scrape specific universities (by index range)
python main.py --scrape --start-index 0 --stop-index 10

# Scrape and export immediately
python main.py --scrape --export
```

### Export Options

```bash
# Export all data
python main.py --export

# Export a specific university
python main.py --export --university "İstinye Üniversitesi"

# Filter by department
python main.py --export --university "İstinye Üniversitesi" --department "Tıp"

# Show 50% scholarship prices
python main.py --export --price-option half

# Apply preference discount
python main.py --export --university "İstinye Üniversitesi" --apply-preference-discount

# Save with different filename
python main.py --export --output "prices"
```

---

## Output Format

The program exports in two formats:

### Excel (.xlsx)
Columns:
- University (University name)
- Department (Department name)
- Score Type (SAY, EA, SÖZ, DİL, TYT)
- Quota (Available seats)
- Score (Minimum score)
- Ranking (Minimum ranking)
- Price (Tuition fee)
- Discounted Price (Discounted fee - if applicable)
- Currency (TRY, USD)

### PDF
Same information in table format.

---

## Project Structure

```
Python-Project-1/
├── main.py                 # Main application
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── models/
│   └── university_models.py  # Data models
├── repository/
│   ├── base_repository.py    # Abstract repository
│   └── repository.py         # MongoDB repository
├── scraper/
│   ├── items.py              # Scrapy item definitions
│   ├── pipelines.py          # Scrapy pipeline
│   ├── settings.py           # Scrapy settings
│   └── spiders/
│       └── university_spider.py  # Main spider
├── util/
│   ├── connect.py            # MongoDB connection
│   ├── notifications.py      # ntfy.sh notifications
│   ├── school_list.py        # University list
│   └── web_scraping.py       # Scraping utilities
└── tests/
    ├── test_integration.py   # Integration tests
    └── test_units.py         # Unit tests
```

---

## Notes

- Preference discounts range from 5% to 60% depending on the university
- 50% scholarship option reduces tuition by half
- All prices are in Turkish Lira (TL) or US Dollars ($)
- Scraping takes approximately 2-3 minutes (76 universities)
- Data is scraped from [universitego.com](https://www.universitego.com)

---

## Running Tests

```bash
# Run all tests
pytest -v

# Run only unit tests
pytest tests/test_units.py -v

# Run only integration tests
pytest tests/test_integration.py -v

# Run with coverage report
pytest --cov=. --cov-report=html
```

---

## Troubleshooting

### MongoDB Connection Error
```
Error: Could not connect to MongoDB
```
**Solution:** Make sure the `MONGO_URI` environment variable is set correctly.

### Scraping Error
```
Error: 404 Not Found
```
**Solution:** Some university URLs may have changed. Please open an issue.

### Notifications Not Working
**Solution:** 
1. Check the `NOTIFY_TOPIC` environment variable
2. Make sure you are subscribed to the same topic in the ntfy.sh app

