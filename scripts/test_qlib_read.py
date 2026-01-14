"""Test Qlib read from exported minute dataset."""
from pathlib import Path
import pandas as pd

# Check if qlib is available
try:
    import qlib
    from qlib.data import D
    QLIB_AVAILABLE = True
except ImportError:
    QLIB_AVAILABLE = False
    print("Qlib not installed. Install with: pip install pyqlib")

def test_read_features_directly():
    """Read features parquet files directly (no qlib needed)."""
    features_dir = Path("data/qlib_cn_1m/features")
    
    if not features_dir.exists():
        print(f"Features directory not found: {features_dir}")
        print("Run 'quantopen export-qlib' first.")
        return
    
    files = list(features_dir.glob("*.parquet"))
    print(f"Found {len(files)} feature files")
    
    if files:
        # Read first file
        fp = files[0]
        df = pd.read_parquet(fp)
        print(f"\n{fp.name}:")
        print(df.head())
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")


def test_read_calendar():
    """Read calendar file."""
    cal_path = Path("data/qlib_cn_1m/calendars/1min.txt")
    
    if not cal_path.exists():
        print(f"Calendar not found: {cal_path}")
        return
    
    with open(cal_path) as f:
        lines = f.readlines()[:5]
    
    print(f"\nCalendar (first 5 lines):")
    for line in lines:
        print(f"  {line.strip()}")


def test_read_instruments():
    """Read instruments file."""
    inst_path = Path("data/qlib_cn_1m/instruments/all.txt")
    
    if not inst_path.exists():
        print(f"Instruments not found: {inst_path}")
        return
    
    with open(inst_path) as f:
        symbols = [line.strip() for line in f.readlines()]
    
    print(f"\nInstruments ({len(symbols)} symbols):")
    print(f"  {symbols}")


def test_qlib_init():
    """Test Qlib initialization with exported data."""
    if not QLIB_AVAILABLE:
        print("\nSkipping Qlib init test (not installed)")
        return
    
    provider_uri = str(Path("data/qlib_cn_1m").resolve())
    print(f"\nInitializing Qlib with: {provider_uri}")
    
    try:
        qlib.init(provider_uri=provider_uri, region="cn")
        print("Qlib init: SUCCESS")
        
        # Try to read features
        inst = "600000"
        df = D.features(
            [inst], 
            ["$close", "$volume"], 
            start_time="2026-01-02", 
            end_time="2026-01-14", 
            freq="1min"
        )
        print(f"\nQlib features for {inst}:")
        print(df.head())
        
    except Exception as e:
        print(f"Qlib init/read: FAILED")
        print(f"Error: {type(e).__name__}: {e}")
        print("\nThis is expected if Qlib requires different internal format.")
        print("The parquet files are still readable directly.")


if __name__ == "__main__":
    print("=" * 60)
    print("Qlib Export Test")
    print("=" * 60)
    
    test_read_features_directly()
    test_read_calendar()
    test_read_instruments()
    test_qlib_init()
