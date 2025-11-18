# BMW Pre-Owned Vehicle Search

An automated inventory monitoring system I built while shopping for my own BMW. When I couldn't find a vehicle matching my exact preferences (specific color combinations, packages, price range), I created this tool to monitor BMW's inventory and alert me when new matching vehicles became available.

## 📖 Project Background

**Origin Story:** While searching for a pre-owned BMW, I was frustrated by:
- Manual daily checks across multiple dealer websites
- No notification system for new inventory matching my preferences
- Complex filtering requirements (specific exterior/interior color combos, packages, price)
- Missing newly listed vehicles that sold within hours

**Solution:** Built this automated system that runs on a schedule, monitors inventory changes, and emails me only when NEW vehicles matching my dream specifications appear.

## 🚫 NOT FOR PUBLIC USE

**This is a portfolio showcase only.**

- ❌ **DO NOT USE THIS CODE** - Not maintained or supported
- ❌ No support, documentation, or assistance provided
- ⚠️ Displayed for portfolio/educational purposes only
- ⚠️ Automated access may conflict with website Terms of Service

This repository demonstrates my technical capabilities in solving real-world problems through automation and data processing.

**The author assumes no liability if you attempt to use this code.**

## Features

- 🔄 **Automated Token Fetching** - Automatically grabs fresh authentication tokens from BMW's website
- 🔍 **Smart Search** - Configurable search with API-level and pandas-level filtering
- 🎨 **Color Preferences** - Define your dream color combinations for instant alerts
- 📧 **Email Notifications** - Get notified only about NEW preferred vehicles
- 💾 **SQLite Database** - Track vehicle history with zero configuration
- 📊 **Excel Export** - Generate organized Excel reports
- 📝 **Comprehensive Logging** - Full execution logs for debugging
- ⏱️ **Rate Limiting** - Respectful delays between requests to avoid overwhelming BMW's servers

## Project Structure

```
BMWSearch/
├── src/                      # Source code
│   ├── main.py              # Main application logic
│   ├── database.py          # SQLite database handler
│   ├── token_fetcher.py     # BMW API token automation
│   └── send_email.py        # Email notification system
├── config.yaml              # Search configuration (version controlled)
├── secrets.ini.example      # Template for email credentials
├── secrets.ini              # Your email credentials (gitignored)
├── run.py                   # Main entry point - run this!
├── pyproject.toml           # Python dependencies
├── output/                  # Generated files (gitignored)
│   ├── excel/              # Excel reports
│   └── database/           # SQLite database
└── logs/                    # Execution logs (gitignored)
```

## Technical Overview

This project demonstrates several technical competencies:

**Technologies Used:**
- Python 3.12+ with modern tooling (uv, pyproject.toml)
- Playwright for browser automation and token extraction
- RESTful API interaction with bearer token authentication
- Pandas for complex data filtering and manipulation
- SQLite for persistent storage without external dependencies
- Email automation with HTML formatting
- YAML-based configuration management
- Structured logging with daily rotation

**Key Technical Achievements:**
- Automated browser-based token extraction from network requests
- Multi-level filtering strategy (API-level + post-processing)
- Stateful change detection using database comparison
- Rate limiting to respect external API constraints
- Configuration-driven architecture for easy customization

## Architecture Highlights

### Multi-Layer Filtering Strategy

The system implements a two-stage filtering approach:

1. **API-Level Filtering** - Broad pre-filtering at the data source
   - Reduces network payload
   - Faster query execution
   - Handles BMW-specific filter constraints

2. **Post-Processing Filters** - Precise custom logic using Pandas
   - Complex boolean conditions
   - Dynamic price range calculations
   - Package code pattern matching

### State Management

- SQLite database tracks all vehicles ever seen
- Change detection algorithm identifies new entries
- Prevents duplicate notifications
- Maintains historical data for analysis

### Configuration Architecture

YAML-based configuration separates concerns:
- Search parameters (location, filters)
- Preference definitions (color combinations)
- API configuration
- Output settings
- Rate limiting controls

## Output Files

### Excel Reports (in `output/excel/`)

- `X4.xlsx` - All filtered vehicles
- `X4_M40i.xlsx` - M40i trim vehicles (if applicable)
- `X4_Preferred.xlsx` - Your preferred color combinations

### Database (in `output/database/`)

- `bmw_vehicles.db` - SQLite database with all vehicle history
- View with: [DB Browser for SQLite](https://sqlitebrowser.org/) or VSCode SQLite extension

### Logs (in `logs/`)

- `YYYY-MM-DD.log` - Daily execution logs with full details

## How It Works

```
1. Fetch fresh BMW API token (automatic)
   ↓
2. Query BMW API with your filters
   ↓
3. API returns broad results (pre-filtered)
   ↓
4. Apply precise pandas filters
   ↓
5. Identify preferred color combinations
   ↓
6. Check database for new vehicles
   ↓
7. Send email alert for NEW preferred vehicles
   ↓
8. Save all results to Excel + Database
```

## Code Organization

```
src/
├── main.py           # Core application logic, filtering, orchestration
├── token_fetcher.py  # Playwright automation for token extraction
├── database.py       # SQLite abstraction layer
└── send_email.py     # Email notification handler
```

### Notable Implementation Details

**Token Fetcher (`token_fetcher.py`)**
- Uses Playwright to intercept network requests
- Extracts bearer tokens from authorization headers
- Headless browser operation
- Configurable timeout and retry logic

**Database Layer (`database.py`)**
- Abstracted SQLite operations
- VIN-based deduplication across collections
- Support for multiple vehicle collections (X3, X4, M40i variants)

**Main Logic (`main.py`)**
- Retry mechanism with exponential backoff
- Paginated API requests with rate limiting
- Complex pandas filtering with regex patterns
- HTML email generation from DataFrame

## License & Usage

**All Rights Reserved** - Portfolio demonstration only.

- This code is NOT available for use, distribution, or modification
- Displayed solely for portfolio and educational purposes
- Not maintained, supported, or intended for production use

**The author provides no warranty and assumes no liability.**

---

## 💡 Lessons Learned

This project taught me:
- **Reverse engineering APIs** through browser network analysis
- **Browser automation** with Playwright for token extraction
- **Two-tier filtering strategies** to optimize API usage and processing
- **Stateful change detection** to avoid notification fatigue
- **Practical rate limiting** to be respectful to external services
- **Configuration-driven design** for maintainability

**Personal Impact:** This wasn't just a coding exercise - it solved a real problem during my vehicle search. Building tools to solve your own problems is one of the best ways to learn.

*Created as a personal project during my BMW vehicle search. Shared here as a portfolio demonstration of practical automation and problem-solving skills.*

