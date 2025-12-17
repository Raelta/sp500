from datetime import datetime
from urllib.parse import quote_plus

def get_google_news_url(date_str, query="S&P 500"):
    """
    Generates a Google News search URL for the specific date.
    date_str: 'YYYY-MM-DD'
    """
    # Format: https://www.google.com/search?q=QUERY&tbs=cdr:1,cd_min:MM/DD/YYYY,cd_max:MM/DD/YYYY&tbm=nws
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = dt.strftime('%m/%d/%Y')
        
        # Proper encoding handles spaces and symbols like '&'
        encoded_query = quote_plus(query)
        
        url = (
            f"https://www.google.com/search?q={encoded_query}"
            f"&tbs=cdr:1,cd_min:{formatted_date},cd_max:{formatted_date}"
            f"&tbm=nws"
        )
        return url
    except Exception:
        return "https://news.google.com"
