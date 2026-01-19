import argparse
import sys

def get_cli_args():
    """
    Parses command-line arguments to override default UI parameters.
    """
    parser = argparse.ArgumentParser(description="SP500 Bump & Slide App")
    
    # Use ignore_unknown to allow streamlit args if any leak, though usually they don't
    # in Streamlit context, sys.argv often contains streamlit-specific flags before '--'
    
    parser.add_argument("-bl", "--bump-len", type=int, help="Bump length (min)")
    parser.add_argument("-bt", "--bump-thresh", type=float, help="Bump threshold")
    parser.add_argument("--bump-type", choices=["percent", "value"], help="Bump threshold type")
    
    parser.add_argument("-sl", "--slide-len", type=int, help="Slide length (min)")
    parser.add_argument("-st", "--slide-thresh", type=float, help="Slide threshold")
    parser.add_argument("--slide-type", choices=["percent", "value"], help="Slide threshold type")
    
    parser.add_argument("--min-bump-vol", type=int, help="Min Bump Volume")
    parser.add_argument("--min-slide-vol", type=int, help="Min Slide Volume")
    
    parser.add_argument("--bump-up-pct", type=float, help="Min % Up Candles in Bump")
    parser.add_argument("--slide-up-pct", type=float, help="Min % Up Candles in Slide")

    # We use parse_known_args to avoid issues with Streamlit's own flags
    # This allows passing arguments like `streamlit run app.py -- --bump-len 10`
    args, _ = parser.parse_known_args()
    return args
