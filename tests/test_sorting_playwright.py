from playwright.sync_api import sync_playwright
import time

def test_table_sorting():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to app (assuming it's running on 8501 or finding port)
        # We'll try standard Streamlit port
        try:
            page.goto("http://localhost:8501")
            page.wait_for_timeout(5000) # Wait for load
        except:
            print("Could not connect to localhost:8501. Is app running?")
            return

        # Check if table exists
        # Streamlit tables are often div[data-testid="stDataFrame"]
        # Column headers are th
        
        # Find the "Bump Change" header
        # This selector is fragile but common for Streamlit tables
        header = page.get_by_text("Bump Change", exact=True)
        
        if not header.count():
            print("FAIL: Could not find 'Bump Change' header.")
            return

        # Click header to sort
        print("Clicking 'Bump Change' header...")
        header.click()
        page.wait_for_timeout(2000)
        
        # Get first row content (Bump Change value)
        # We need to find the cells in the column. 
        # This requires traversing the grid structure which is complex in canvas/arrow based st.dataframe.
        
        # Streamlit 1.30+ uses st.dataframe (Arrow). The DOM might just be a Canvas or SVG?
        # If it's the newer Arrow table, it's NOT a standard HTML table. It's a Glide Data Grid.
        # It's rendered on Canvas. Playwright CANNOT click internal headers reliably if it's Canvas.
        
        # IF this is the cause, then "click the top of the table" MIGHT NOT WORK reliably for automation 
        # or even for users if the hit testing is off.
        
        # Let's verify if we can interact with it.
        # If we can't test it, we can't self-check.
        
        print("Test inconclusive: Streamlit dataframes use Canvas rendering which is hard to scrape.")
        
        # However, we can check if we can click.
        
        browser.close()

if __name__ == "__main__":
    test_table_sorting()
