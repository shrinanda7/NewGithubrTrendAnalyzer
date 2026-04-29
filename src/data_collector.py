import os
import requests
from datetime import datetime, timedelta

def download_gh_archive(year, month, day, hour, output_dir):
    """
    Downloads a single hour of GH Archive data.
    Format: YYYY-MM-DD-H.json.gz
    """
    filename = f"{year}-{month:02d}-{day:02d}-{hour}.json.gz"
    url = f"https://data.gharchive.org/{filename}"
    output_path = os.path.join(output_dir, filename)
    
    if os.path.exists(output_path):
        print(f"File {filename} already exists. Skipping.")
        return True

    print(f"Downloading {filename}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Successfully downloaded {filename}")
        return True
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        return False

def collect_data(target_gb=1.0, output_dir="data"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Start from a recent date
    current_date = datetime.now() - timedelta(days=2) # 2 days ago to ensure data availability
    downloaded_size = 0
    target_bytes = target_gb * 1024 * 1024 * 1024
    
    while downloaded_size < target_bytes:
        year = current_date.year
        month = current_date.month
        day = current_date.day
        
        for hour in range(24):
            if downloaded_size >= target_bytes:
                break
                
            success = download_gh_archive(year, month, day, hour, output_dir)
            if success:
                filename = f"{year}-{month:02d}-{day:02d}-{hour}.json.gz"
                file_size = os.path.getsize(os.path.join(output_dir, filename))
                downloaded_size += file_size
                print(f"Current total size: {downloaded_size / (1024*1024):.2f} MB")
            
        current_date -= timedelta(days=1)

if __name__ == "__main__":
    # We will download ~1GB of compressed data which will be much larger when processed
    collect_data(target_gb=0.2) # Reducing to 0.2GB for the demo to avoid long waits, user can increase it
