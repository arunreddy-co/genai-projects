import csv
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS startups"))
    conn.execute(text("""
        CREATE TABLE startups (
            id SERIAL PRIMARY KEY,
            company_name TEXT,
            city TEXT,
            industry TEXT,
            funding_amount_cr NUMERIC,
            funding_round TEXT,
            lead_investor TEXT,
            founded_year INTEGER,
            num_employees INTEGER,
            status TEXT
        )
    """))
    conn.commit()

    with open("data/startup_funding.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(text("""
                INSERT INTO startups (company_name, city, industry, funding_amount_cr, funding_round, lead_investor, founded_year, num_employees, status)
                VALUES (:name, :city, :industry, :amount, :round, :investor, :year, :employees, :status)
            """), {
                "name": row["company_name"],
                "city": row["city"],
                "industry": row["industry"],
                "amount": float(row["funding_amount_cr"]),
                "round": row["funding_round"],
                "investor": row["lead_investor"],
                "year": int(row["founded_year"]),
                "employees": int(row["num_employees"]),
                "status": row["status"]
            })
    conn.commit()
    print("Data loaded successfully! Inserted rows into 'startups' table.")
