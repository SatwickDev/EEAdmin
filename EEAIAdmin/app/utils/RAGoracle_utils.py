# app/utils/RAGoracle_utils.py

import cx_Oracle
from app.utils import app_config  # ✅ For running directly as script

def fetch_oracle_data():
    # Use value from config (recommended) OR hardcoded (acceptable for local test)
    cx_Oracle.init_oracle_client(lib_dir=r"C:\Users\vijayan\Downloads\instantclient-basic-windows.x64-23.6.0.24.10\instantclient_23_6")

    # Use raw string literals or escape backslashes, and avoid formatting strings inside f-strings unnecessarily
    conn = cx_Oracle.connect(
        "CETRX",                  # username
        "CETRX",                  # password
        "DEV-SCF:1521/DSCF"       # connection string
    )

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cetrx.trx_inbox FETCH FIRST 100 ROWS ONLY")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows if any(row)]

if __name__ == "__main__":
    from pprint import pprint
    records = fetch_oracle_data()
    pprint(records[:2])  # show first 2 records for verification
