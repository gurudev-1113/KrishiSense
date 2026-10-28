"""
Builds prices.db (SQLite) from the raw crop CSV.
Run this ONCE (or whenever the CSV updates):

    python init_db.py

Requires Dakshina_Kannada_Crop_Dataset_Extended.csv to be in this same folder.
"""
import sqlite3
import pandas as pd
import os
import numpy as np

CSV_PATH = "Dakshina_Kannada_Crop_Dataset_Extended.csv"
DB_PATH = "prices.db"

if not os.path.exists(CSV_PATH):
    # Try alternative filename if extended doesn't exist
    alt_path = "Dakshina_Kannada_Crop_Dataset_Updated.csv"
    if os.path.exists(alt_path):
        CSV_PATH = alt_path
        print(f"✅ Using alternative file: {alt_path}")
    else:
        raise FileNotFoundError(
            f"❌ Couldn't find {CSV_PATH} or {alt_path} in this folder. "
            "Copy your dataset CSV here before running init_db.py."
        )

print(f"📂 Reading CSV: {CSV_PATH}")
df = pd.read_csv(CSV_PATH)

print(f"📋 Original columns: {df.columns.tolist()}")
print(f"📊 Shape: {df.shape}")

# ============================================================
# 1. FIX COLUMN NAMES - Handle different naming conventions
# ============================================================
# Check if columns exist with different names
column_mapping = {}
for col in df.columns:
    col_lower = col.lower()
    if col_lower == 'modal_price' and 'Modal_Price' not in df.columns:
        column_mapping[col] = 'Modal_Price'
    elif col_lower == 'arrival_qty' and 'Arrival_Qty' not in df.columns:
        column_mapping[col] = 'Arrival_Qty'
    elif col_lower == 'commodity' and 'Commodity' not in df.columns:
        column_mapping[col] = 'Commodity'
    elif col_lower == 'market' and 'Market' not in df.columns:
        column_mapping[col] = 'Market'
    elif col_lower == 'variety' and 'Variety' not in df.columns:
        column_mapping[col] = 'Variety'
    elif col_lower == 'source' and 'Source' not in df.columns:
        column_mapping[col] = 'Source'
    elif col_lower == 'date' and 'Date' not in df.columns:
        column_mapping[col] = 'Date'
    elif col_lower == 'state' and 'State' not in df.columns:
        column_mapping[col] = 'State'
    elif col_lower == 'district' and 'District' not in df.columns:
        column_mapping[col] = 'District'
    elif col_lower == 'rainfall_mm' and 'Rainfall_mm' not in df.columns:
        column_mapping[col] = 'Rainfall_mm'
    elif col_lower == 'festival_flag' and 'Festival_Flag' not in df.columns:
        column_mapping[col] = 'Festival_Flag'
    elif col_lower == 'month_name' and 'Month_Name' not in df.columns:
        column_mapping[col] = 'Month_Name'

if column_mapping:
    df.rename(columns=column_mapping, inplace=True)
    print(f"🔄 Renamed columns: {column_mapping}")

# ============================================================
# 2. CHECK REQUIRED COLUMNS
# ============================================================
required_cols = ['Date', 'Commodity', 'Market', 'Modal_Price']
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    print(f"❌ Error: Missing required columns: {missing_cols}")
    print(f"📋 Available columns: {df.columns.tolist()}")
    raise ValueError(f"Missing required columns: {missing_cols}")

# ============================================================
# 3. ADD MISSING COLUMNS THAT THE MODEL EXPECTS
# ============================================================
# Add columns that the model expects but may not be in the dataset
model_columns = ['Rainfall_mm', 'Festival_Flag', 'State', 'District']
for col in model_columns:
    if col not in df.columns:
        if col == 'State':
            df[col] = 'Karnataka'
            print(f"✅ Added column '{col}' with default value 'Karnataka'")
        elif col == 'District':
            # Try to get district from Market or set default
            if 'Market' in df.columns:
                # Create a mapping from market to district
                market_district_map = {
                    'Bantwal': 'Dakshina Kannada',
                    'Belthangady': 'Dakshina Kannada',
                    'Mangalore': 'Dakshina Kannada',
                    'Moodbidri': 'Dakshina Kannada',
                    'Puttur': 'Dakshina Kannada',
                    'Sullia': 'Dakshina Kannada',
                    'Uppinangady': 'Dakshina Kannada'
                }
                df['District'] = df['Market'].map(market_district_map).fillna('Dakshina Kannada')
                print(f"✅ Added column 'District' based on Market mapping")
            else:
                df[col] = 'Dakshina Kannada'
                print(f"✅ Added column '{col}' with default value 'Dakshina Kannada'")
        else:
            df[col] = 0
            print(f"✅ Added missing column '{col}' with default value 0")

# ============================================================
# 4. ENSURE Arrival_Qty EXISTS
# ============================================================
if 'Arrival_Qty' not in df.columns:
    # Try case-insensitive match
    alt_col = next((c for c in df.columns if c.lower() == 'arrival_qty'), None)
    if alt_col:
        df.rename(columns={alt_col: 'Arrival_Qty'}, inplace=True)
        print(f"🔄 Renamed '{alt_col}' to 'Arrival_Qty'")
    else:
        df['Arrival_Qty'] = 0
        print("✅ Added missing column 'Arrival_Qty' with default value 0")

# ============================================================
# 5. CONVERT DATE COLUMN
# ============================================================
try:
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    print(f"✅ Date column converted successfully")
except Exception as e:
    print(f"⚠️ Date conversion failed: {e}")
    print("📋 Available columns:", df.columns.tolist())
    raise

# ============================================================
# 6. DATA CLEANING - ENHANCED VERSION
# ============================================================

# Record original shape for reporting
original_shape = df.shape

# REMOVE ROWS WITH PLACEHOLDER VALUES (Modal_Price = 1 in your data)
# This is critical - your dataset has rows with Modal_Price = 1 as placeholders
df = df[df['Modal_Price'] > 1]
print(f"📊 Removed rows with placeholder price (<=1): {original_shape[0] - df.shape[0]} rows removed")

# ADDED: Also check for rows where Min_Price, Max_Price, and Modal_Price are all 1
# This catches the specific bad row: 2024-10-18, Belthangady, Banana with 1,1,1
if 'Min_Price' in df.columns and 'Max_Price' in df.columns:
    before = df.shape[0]
    df = df[~((df['Min_Price'] == 1) & (df['Max_Price'] == 1) & (df['Modal_Price'] == 1))]
    removed = before - df.shape[0]
    if removed > 0:
        print(f"📊 Removed {removed} rows where all price columns were 1 (complete placeholder)")

# ADDED: Remove rows where Modal_Price is suspiciously low (less than 10)
# This catches any other placeholder-like values
df = df[df['Modal_Price'] >= 10]
print(f"📊 Removed rows with Modal_Price < 10: {df.shape[0]} rows remaining")

# Sort and reset index
df = df.sort_values(["Commodity", "Market", "Date"]).reset_index(drop=True)

# Handle NaN values in Modal_Price
df['Modal_Price'] = df['Modal_Price'].fillna(df['Modal_Price'].median())

# Clean up price values - ensure they're reasonable
df['Modal_Price'] = df['Modal_Price'].clip(lower=1)  # Remove zero or negative prices

# Remove rows with invalid prices (too high - likely errors)
# You can adjust these thresholds based on your data
df = df[df['Modal_Price'] < 1000000]  # Remove prices > 10,00,000 (likely errors)
df = df[df['Modal_Price'] > 0]  # Remove zero or negative prices

# If Variety column exists, fill NaN with 'Local'
if 'Variety' in df.columns:
    df['Variety'] = df['Variety'].fillna('Local')
else:
    df['Variety'] = 'Local'
    print("✅ Added 'Variety' column with default 'Local'")

print(f"📊 After cleaning: {df.shape} rows (removed {original_shape[0] - df.shape[0]} total rows)")

# ============================================================
# 7. HANDLE FESTIVAL_FLAG - ENSURE IT'S PROPERLY SET
# ============================================================
# If Festival_Flag column exists but has NaN values, fill with 0
if 'Festival_Flag' in df.columns:
    df['Festival_Flag'] = df['Festival_Flag'].fillna(0)
    # Ensure it's integer type
    df['Festival_Flag'] = df['Festival_Flag'].astype(int)

# ============================================================
# 8. HANDLE RAINFALL_MM - ENSURE IT'S PROPERLY SET
# ============================================================
if 'Rainfall_mm' in df.columns:
    df['Rainfall_mm'] = df['Rainfall_mm'].fillna(0)
    # Ensure it's float type
    df['Rainfall_mm'] = df['Rainfall_mm'].astype(float)

print(f"📊 Final shape: {df.shape}")

# ============================================================
# 9. CREATE DATABASE
# ============================================================
conn = sqlite3.connect(DB_PATH)

# Write data to table
df.to_sql("prices", conn, if_exists="replace", index=False)

# Create helpful indexes for faster queries
print("📊 Creating indexes...")
conn.execute("CREATE INDEX IF NOT EXISTS idx_commodity_market_date ON prices (Commodity, Market, Date);")
conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON prices (Date);")
conn.execute("CREATE INDEX IF NOT EXISTS idx_commodity_market ON prices (Commodity, Market);")
conn.execute("CREATE INDEX IF NOT EXISTS idx_month ON prices (strftime('%m', Date));")
conn.execute("CREATE INDEX IF NOT EXISTS idx_commodity ON prices (Commodity);")
conn.execute("CREATE INDEX IF NOT EXISTS idx_market ON prices (Market);")
conn.execute("CREATE INDEX IF NOT EXISTS idx_year ON prices (strftime('%Y', Date));")
conn.commit()
conn.close()

# ============================================================
# 10. PRINT SUMMARY
# ============================================================
print(f"\n✅ Done. Loaded {len(df)} rows into {DB_PATH}.")
print(f"\n📊 Summary:")
print(f"   🌾 Commodities ({len(df['Commodity'].unique())}):")
for commodity in sorted(df['Commodity'].unique()):
    count = len(df[df['Commodity'] == commodity])
    print(f"      - {commodity}: {count} records")
print(f"\n   🏪 Markets ({len(df['Market'].unique())}):")
for market in sorted(df['Market'].unique()):
    count = len(df[df['Market'] == market])
    print(f"      - {market}: {count} records")

if "Source" in df.columns:
    print("\n   📋 Source breakdown:")
    source_counts = df["Source"].value_counts()
    for source, count in source_counts.items():
        print(f"      {source}: {count} rows")

# Check date range
date_min = df['Date'].min()
date_max = df['Date'].max()
days = (pd.to_datetime(date_max) - pd.to_datetime(date_min)).days
print(f"\n📅 Date range: {date_min} to {date_max} ({days} days)")

# Check yearly distribution
print("\n📊 Yearly data distribution:")
yearly_counts = df.groupby(pd.to_datetime(df['Date']).dt.year).size()
for year, count in yearly_counts.items():
    print(f"   {year}: {count} records")

# Check monthly data distribution
print("\n📊 Monthly data distribution:")
monthly_counts = df.groupby(pd.to_datetime(df['Date']).dt.month).size()
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
for i, count in enumerate(monthly_counts):
    if i < 12:
        print(f"   {month_names[i]}: {count} records")

# Check data by commodity
print("\n🌾 Data by Commodity:")
commodity_counts = df.groupby('Commodity').size().sort_values(ascending=False)
for commodity, count in commodity_counts.head(10).items():
    print(f"   {commodity}: {count} records")

# Check for null values
print("\n🔍 Null value check:")
for col in df.columns:
    null_count = df[col].isnull().sum()
    if null_count > 0:
        print(f"   ⚠️ {col}: {null_count} null values")

# ============================================================
# 11. CHECK SPECIFIC COMMODITIES AND MARKETS
# ============================================================
print("\n📊 Data availability check:")
for commodity in df['Commodity'].unique():
    markets = df[df['Commodity'] == commodity]['Market'].unique()
    print(f"   {commodity}: {len(markets)} markets - {', '.join(markets[:3])}{'...' if len(markets) > 3 else ''}")
    
    # Check how many years of data
    years = df[df['Commodity'] == commodity]['Date'].str[:4].unique()
    print(f"      Years: {sorted(years)}")

print(f"\n💡 Tip: Run 'python app.py' to start the Flask server.")
print(f"   Make sure your trained models are in the 'saved_models' folder.")