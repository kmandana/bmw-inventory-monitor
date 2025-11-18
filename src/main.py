import json
import os
import time
import logging
import warnings
import requests
import traceback
import pandas as pd
import yaml
import configparser
from typing import Optional, Dict, Any
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning

from send_email import send_email
from token_fetcher import get_bmw_token
from database import BMWDatabase
# Suppress only the NotOpenSSLWarning
warnings.filterwarnings('ignore', category=InsecureRequestWarning)
warnings.filterwarnings("ignore")


def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.yaml file
    
    Returns:
        Dictionary with loaded configuration
    """
    if not os.path.exists('config.yaml'):
        raise FileNotFoundError(
            "config.yaml not found! Please ensure config.yaml exists in the project directory.\n"
            "The config.yaml file should be version controlled and contain your search preferences."
        )
    
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def load_secrets() -> configparser.ConfigParser:
    """
    Load secrets from secrets.ini file
    
    Returns:
        ConfigParser object with email credentials
    """
    if not os.path.exists('secrets.ini'):
        raise FileNotFoundError(
            "secrets.ini not found! Please create one from secrets.ini.example:\n"
            "  cp secrets.ini.example secrets.ini\n"
            "Then edit secrets.ini with your email credentials."
        )
    
    config = configparser.ConfigParser()
    config.read('secrets.ini')
    return config


def calculate_api_price_ranges(max_price: int) -> list:
    """
    Automatically calculate which BMW API price range buckets to request
    based on the maximum price.
    
    BMW API uses specific price range strings. This function determines
    which ranges to include based on your max_price.
    
    Args:
        max_price: Maximum price in dollars (e.g., 49999)
    
    Returns:
        List of price range strings to send to BMW API
    
    Example:
        calculate_api_price_ranges(49999) returns:
        ["Other", "$10,000 - $19,999", "$20,000 - $29,999", 
         "$30,000 - $39,999", "$40,000 - $49,999"]
    """
    # All BMW API price ranges in order
    all_ranges = [
        ("Other", 0, 9999),
        ("$10,000 - $19,999", 10000, 19999),
        ("$20,000 - $29,999", 20000, 29999),
        ("$30,000 - $39,999", 30000, 39999),
        ("$40,000 - $49,999", 40000, 49999),
        ("$50,000 - $59,999", 50000, 59999),
        ("$60,000 - $69,999", 60000, 69999),
        ("$70,000 - $79,999", 70000, 79999),
        ("$80,000 - $89,999", 80000, 89999),
        ("$90,000 - $99,999", 90000, 99999),
        ("$100,000 - $149,999", 100000, 149999),
        ("$150,000 or more", 150000, float('inf')),
    ]
    
    # Include all ranges where the range minimum is <= max_price
    selected_ranges = []
    for range_str, range_min, range_max in all_ranges:
        if range_min <= max_price:
            selected_ranges.append(range_str)
        else:
            break  # Stop once we exceed max_price
    
    return selected_ranges


def setup_logger(log_dir: str = 'logs'):
    """
    Sets up a logger that writes logs to a file named with today's date.
    
    Args:
        log_dir: Directory to store log files
    """
    # Get today's date in YYYY-MM-DD format
    today_date = datetime.now().strftime('%Y-%m-%d')

    os.makedirs(log_dir, exist_ok=True)

    log_file_name = f'{log_dir}/{today_date}.log'

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Create a file handler for writing logs to a file
        file_handler = logging.FileHandler(log_file_name)
        file_handler.setLevel(logging.INFO)

        # Define the log message format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Add the file handler to the logger
        logger.addHandler(file_handler)

    return logger


def retry_operation(callable_func, logger, args=None, kwargs=None, retries=5, initial_wait=10, backoff_factor=2):
    """
    Retry operation with exponential backoff.

    :param callable_func: The function to execute that might fail.
    :param logger: The logger to use for logging.
    :param args: Tuple of arguments to pass to the callable.
    :param kwargs: Dictionary of keyword arguments to pass to the callable.
    :param retries: Maximum number of retries.
    :param initial_wait: Initial wait time between retries in seconds.
    :param backoff_factor: Factor by which to multiply wait time for each retry.
    """
    args = args or ()
    kwargs = kwargs or {}
    attempt = 0

    while attempt < retries:
        try:
            return callable_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed with error: {e}")
            wait_time = initial_wait * backoff_factor ** attempt
            time.sleep(wait_time)
            attempt += 1
            if attempt == retries:
                logger.error("Max retries reached. Operation failed.")
                logger.error(traceback.format_exc())
                raise e


def api_call(url, payload, headers):
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()  # Will raise an HTTPError for bad responses
    return response.json()




def get_total_count(url, payload, headers, logger):
    data = retry_operation(
        api_call,
        logger,
        args=(url, payload, headers),
        retries=3,
        initial_wait=1,
        backoff_factor=2,
    )
    return data["totalRecords"]


def get_total_vehicles(url, payload, headers, total_vehicles, logger, rate_limit_delay=2):
    """
    Fetch all vehicles with rate limiting to be respectful to BMW's servers
    
    Args:
        rate_limit_delay: Minimum seconds to wait between API requests (default: 2)
    """
    all_vehicles_data = []
    for i in range(0, total_vehicles, 100):
        payload["pageIndex"] = i
        data = retry_operation(
            api_call,
            logger,
            args=(url, payload, headers),
            retries=3,
            initial_wait=1,
            backoff_factor=2,
        )
        vehicles = data["vehicles"]
        if vehicles:
            all_vehicles_data.extend(vehicles)
        
        # Rate limiting: wait between requests (except for last one)
        if i + 100 < total_vehicles:
            logger.debug(f"Rate limiting: waiting {rate_limit_delay} seconds before next request")
            time.sleep(rate_limit_delay)
    
    vehicles_df = pd.DataFrame(all_vehicles_data)
    return vehicles_df


def filter_data(vehicles_df, config, model):
    """
    Filter vehicles based on configuration
    
    Args:
        vehicles_df: DataFrame containing vehicle data
        config: Configuration dictionary from YAML
        model: Model name (e.g., 'X3', 'X4')
    
    Returns:
        Tuple of (filtered_df, preferred_cars_df, m40i_df)
    """
    required_cols = ["year", "type", "model", "trimDescription", "stockNumber", "interior", "exterior", "interiorMeta",
                     "exteriorMeta", "odometer", "vdpUrl", "internetPrice", "msrp", "labelPrice", "packageDescriptions",
                     "packageOptionDescriptions", "nonPackageOptionDescriptions", "accessoryDescriptions", "vin",
                     "distance", "allCodes"]

    # Filter by max price (from pandas_filters)
    pandas_filters = config['search']['pandas_filters']
    max_price = pandas_filters['max_price']
    filtered_df = vehicles_df[vehicles_df["internetPrice"] <= max_price]
    
    # Exclude exterior colors from config
    exclude_colors = pandas_filters.get('exclude_exterior_meta', [])
    for color in exclude_colors:
        filtered_df = filtered_df[filtered_df["exteriorMeta"] != color]
    
    filtered_df = filtered_df[required_cols]
    
    # Include only vehicles with specific package codes (or null package codes)
    include_packages = pandas_filters.get('include_packages', [])
    if include_packages:
        # Build regex pattern from package codes
        package_codes = '|'.join([pkg['code'] for pkg in include_packages])
        # Keep vehicles that HAVE these packages OR have null/missing allCodes
        condition = filtered_df['allCodes'].str.contains(package_codes, na=False) | filtered_df['allCodes'].isna()
        filtered_df = filtered_df[condition]

    filtered_df.rename(columns={'vin': '_id'}, inplace=True)

    # Build preference conditions from config
    preference_combinations = config['preferences'].get('combinations', [])
    preference_conditions = []
    
    for combo in preference_combinations:
        cond = pd.Series([True] * len(filtered_df), index=filtered_df.index)
        
        # Check exterior_contains (partial match)
        if 'exterior_contains' in combo:
            cond = cond & filtered_df["exterior"].str.contains(combo['exterior_contains'], na=False)
        
        # Check exterior_meta (exact match)
        if 'exterior_meta' in combo:
            cond = cond & (filtered_df["exteriorMeta"] == combo['exterior_meta'])
        
        # Check interior_meta (exact match)
        if 'interior_meta' in combo:
            cond = cond & (filtered_df["interiorMeta"] == combo['interior_meta'])
        
        preference_conditions.append(cond)
    
    # Combine all preference conditions with OR
    if preference_conditions:
        preference_condition = preference_conditions[0]
        for cond in preference_conditions[1:]:
            preference_condition = preference_condition | cond
        preferred_cars_df = filtered_df[preference_condition]
    else:
        preferred_cars_df = pd.DataFrame()
    
    preferred_cars_df.reset_index(drop=True, inplace=True)
    filtered_df.reset_index(drop=True, inplace=True)

    # Check if model requires M40i separation
    separate_m40i_models = config['model_specific'].get('separate_m40i', [])
    if model in separate_m40i_models:
        m40i_df = filtered_df[filtered_df["trimDescription"] == "M40i"]
        filtered_df = filtered_df[filtered_df["trimDescription"] != "M40i"]
        filtered_df.reset_index(drop=True, inplace=True)
        m40i_df.reset_index(drop=True, inplace=True)
        return filtered_df, preferred_cars_df, m40i_df
    
    return filtered_df, preferred_cars_df, pd.DataFrame()




def generate_html(df):
    html_template = """
    <html>
    <head>
    <style>
      table {
        font-family: Arial, sans-serif;
        border-collapse: collapse;
        width: 100%;
      }
      td, th {
        border: 1px solid #dddddd;
        text-align: left;
        padding: 8px;
      }
      tr:nth-child(even) {
        background-color: #f2f2f2;
      }
    </style>
    </head>
    <body>
    <h2>Vehicle Inventory</h2>
    <table>
      <tr>
        <th>Model + Trim</th>
        <th>Year</th>
        <th>Type</th>
        <th>Exterior</th>
        <th>Interior</th>
        <th>Odometer</th>
        <th>Internet Price</th>
        <th>Package Descriptions</th>
        <th>Distance</th>
        <th>VDP URL</th>
      </tr>
    """

    # Loop
    for index, row in df.iterrows():
        model_trim = f"{row['model']} {row['trimDescription']}"
        html_template += f"""
      <tr>
        <td>{model_trim}</td>
        <td>{row['year']}</td>
        <td>{row['type']}</td>
        <td>{row['exterior']}</td>
        <td>{row['interior']}</td>
        <td>{row['odometer']}</td>
        <td>${row['internetPrice']}</td>
        <td>{row['packageDescriptions']}</td>
        <td>{row['distance']} miles</td>
        <td><a href="{row['vdpUrl']}">View Details</a></td>
      </tr>
    """

    html_template += """
    </table>
    </body>
    </html>
    """

    return html_template


def main():
    # Load configuration and secrets
    config = load_config()
    secrets = load_secrets()
    
    # Setup output directories
    excel_dir = config['output']['excel_dir']
    database_dir = config['output']['database_dir']
    logs_dir = config['output']['logs_dir']
    
    os.makedirs(excel_dir, exist_ok=True)
    os.makedirs(database_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    
    logger = setup_logger(logs_dir)
    
    # Read search parameters from config.yaml
    page_index = 0
    postal_code = config['search']['postal_code']
    radius = config['search']['radius']
    
    # API filters
    api_filters = config['search']['api_filters']
    models = api_filters['series']
    years = api_filters['years']
    drive_train = api_filters['drivetrain']
    vehicle_type = api_filters['type']
    body_style = api_filters.get('body_style', [])
    transmission = api_filters.get('transmission', [])
    fuel_type = api_filters.get('fuel_type', [])
    exterior_color = api_filters.get('exterior_color', [])
    interior_color = api_filters.get('interior_color', [])
    option = api_filters.get('options', [])
    max_odometer = api_filters['odometer']
    
    # Calculate API price ranges from max_price
    max_price = config['search']['pandas_filters']['max_price']
    api_price_ranges = calculate_api_price_ranges(max_price)
    
    logger.info(f"Search config: postal_code={postal_code}, models={models}, years={years}, max_price=${max_price}")
    logger.info(f"Auto-calculated price ranges: {api_price_ranges}")
    
    # Automatically fetch fresh BMW API token
    logger.info("Fetching fresh BMW API token...")
    bearer_token = get_bmw_token(headless=True, logger=logger)
    
    if not bearer_token:
        logger.error("Failed to fetch BMW API token. Exiting.")
        return
    
    logger.info("Successfully obtained fresh token")
    
    # API configuration
    url = config['api']['url']
    headers = {
        'Origin': 'https://www.bmwusa.com',
        'Referer': 'https://www.bmwusa.com/',
        'Authorization': f'Bearer {bearer_token}',
    }
    payload = {
        "pageIndex": page_index,
        "PageSize": config['api']['page_size'],
        "postalCode": postal_code,
        "radius": radius,
        "sortBy": config['api']['sort_by'],
        "sortDirection": config['api']['sort_direction'],
        "formatResponse": False,
        "includeFacets": True,
        "includeDealers": True,
        "includeVehicles": True,
        "filters": [
            {
                "name": "Series",
                "values": models
            },
            {
                "name": "Price",
                "values": api_price_ranges
            },
            {
                "name": "Year",
                "values": years
            },
            {
                "name": "Odometer",
                "values": [max_odometer]
            },
            {
                "name": "Drivetrain",
                "values": drive_train
            },
            {
                "name": "Type",
                "values": vehicle_type
            },
            {
                "name": "BodyStyle",
                "values": body_style
            },
            {
                "name": "Transmission",
                "values": transmission
            },
            {
                "name": "FuelType",
                "values": fuel_type
            },
            {
                "name": "ExteriorColor",
                "values": exterior_color
            },
            {
                "name": "InteriorColor",
                "values": interior_color
            },
            {
                "name": "Option",
                "values": option
            }
        ]
    }
    total_vehicles = get_total_count(url, payload, headers, logger)
    logger.info(f"Total vehicles found: {total_vehicles}")
    
    # Rate limiting configuration
    rate_limit_delay = config.get('rate_limiting', {}).get('delay_between_requests', 2)
    logger.info(f"Using rate limit: {rate_limit_delay} seconds between requests")
    
    vehicles_df = get_total_vehicles(url, payload, headers, total_vehicles, logger, rate_limit_delay)
    vehicles_df, preferred_cars_df, m40i_df = filter_data(vehicles_df, config, models[0])
    
    # Save Excel files to output directory
    excel_file = os.path.join(excel_dir, f"{models[0]}.xlsx")
    vehicles_df.to_excel(excel_file, index=False)
    logger.info(f"Saved {len(vehicles_df)} vehicles to {excel_file}")
    
    if not m40i_df.empty:
        m40i_file = os.path.join(excel_dir, f"{models[0]}_M40i.xlsx")
        m40i_df.to_excel(m40i_file, index=False)
        logger.info(f"Saved {len(m40i_df)} M40i vehicles to {m40i_file}")
    
    preferred_file = os.path.join(excel_dir, f"{models[0]}_Preferred.xlsx")
    preferred_cars_df.to_excel(preferred_file, index=False)
    logger.info(f"Saved {len(preferred_cars_df)} preferred vehicles to {preferred_file}")

    # Initialize SQLite database
    db_file = os.path.join(database_dir, config['database']['file'])
    db = BMWDatabase(db_file, logger=logger)

    # Check for new preferred vehicles (not in database)
    collections = ["X3", "X4", "X3_M40i", "X4_M40i"]
    not_found_vins = []
    if not preferred_cars_df.empty:
        for _, row in preferred_cars_df.iterrows():
            vin = row['_id']
            
            # Check if VIN exists in any of the collections
            if not db.vin_exists_in_collections(vin, collections):
                not_found_vins.append(vin)
            else:
                logger.debug(f"VIN already in database: {vin}")

        df_not_found = preferred_cars_df[preferred_cars_df['_id'].isin(not_found_vins)]
        logger.info(f"New preferred vehicles found: {df_not_found.shape[0]}")
        
        if df_not_found.shape[0] > 0:
            html_message = generate_html(df_not_found)
            to_email = secrets.get('EMAIL', 'to_email')
            email_subject = config['email']['subject']
            send_email(email_subject, "plain_message", html_message, to_email, preferred_file)
            logger.info(f"Email sent to {to_email} with {df_not_found.shape[0]} new preferred vehicles")

    # Insert vehicles into SQLite database
    db.insert_vehicles(vehicles_df, models[0])
    if not m40i_df.empty:
        db.insert_vehicles(m40i_df, f"{models[0]}_M40i")
    
    # Close database connection
    db.close()



if __name__ == '__main__':
    main()
