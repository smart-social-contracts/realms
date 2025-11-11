"""
Step 1: Fetch data (async example with HTTP outcall)

This step demonstrates an async operation that fetches data from an external source.
"""

from kybra import ic

def async_task():
    """Async task to fetch data from external API."""
    from main import download_file_from_url
    
    url = "https://gist.githubusercontent.com/RichardBray/2e3ab4da089d2d9d5a6016b60c53e33a/raw/f307f2e1bb09bd42b6b10d7e07cd26ad3764463b/example-data.json"
    ic.print(f"📥 Step 1: Fetching data from {url}...")
    
    try:
        # Download the file (async operation using IC HTTP outcalls)
        result = yield download_file_from_url(url)
        
        ic.print(f"✅ Step 1 complete! Downloaded {len(result)} bytes")
        
        # In a real implementation, you could store this in an entity for the next step
        # For now, we just return the result
        return {"status": "success", "size": len(result), "data": result[:100]}
        
    except Exception as e:
        ic.print(f"❌ Step 1 failed: {str(e)}")
        raise
