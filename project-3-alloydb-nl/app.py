import os
import re
import json
from flask import Flask, request, jsonify, render_template_string
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "genai-apac-track1-491517")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

vertexai.init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel("gemini-2.5-flash")

TABLE_SCHEMA = """
Table: startups
Columns:
- id (SERIAL, primary key)
- company_name (TEXT) - name of the startup
- city (TEXT) - city where HQ is located (e.g., Bangalore, Mumbai, Delhi, Chennai, Pune, Hyderabad, Gurugram, Noida, Jaipur)
- industry (TEXT) - sector (e.g., Fintech, E-commerce, Edtech, SaaS, Health Tech, Logistics, AI, D2C Retail, Mobility, EV, Insurtech, Food Delivery, etc.)
- funding_amount_cr (NUMERIC) - total funding raised in Indian Crores (₹)
- funding_round (TEXT) - latest round (Seed, Series A-K, IPO, Pre-IPO, Bootstrapped)
- lead_investor (TEXT) - primary investor name
- founded_year (INTEGER) - year the company was founded
- num_employees (INTEGER) - approximate number of employees
- status (TEXT) - current status (Active, Struggling, Inactive, Acquired, Downsizing)
"""

SYSTEM_PROMPT = f"""You are a SQL expert. Convert natural language questions about Indian startup funding data into PostgreSQL queries.

Here is the database schema:
{TABLE_SCHEMA}

Rules:
1. Return ONLY the SQL query, nothing else. No explanations, no markdown, no backticks.
2. Only generate SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, or any destructive query.
3. Use ILIKE for text matching to be case-insensitive.
4. When user says "crores" or "cr", the column is funding_amount_cr.
5. If a question is unclear, make your best interpretation.
6. Always limit results to 20 rows unless the user specifies otherwise.
7. For "top" or "highest" questions, use ORDER BY ... DESC LIMIT.
8. For aggregations, use appropriate GROUP BY clauses.

Examples:
Q: Which startups are in Bangalore?
A: SELECT company_name, industry, funding_amount_cr, status FROM startups WHERE city ILIKE '%Bangalore%' LIMIT 20

Q: What is the total funding in fintech?
A: SELECT SUM(funding_amount_cr) as total_funding_cr FROM startups WHERE industry ILIKE '%Fintech%'

Q: Show me the top 5 most funded startups
A: SELECT company_name, city, industry, funding_amount_cr, lead_investor FROM startups ORDER BY funding_amount_cr DESC LIMIT 5

Q: How many startups are struggling?
A: SELECT COUNT(*) as count, city FROM startups WHERE status ILIKE '%Struggling%' GROUP BY city ORDER BY count DESC
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StartupIQ - Indian Startup Funding Explorer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f0f2f5; min-height: 100vh; display: flex; flex-direction: column; }
        .header { background: linear-gradient(135deg, #1a73e8, #0d47a1); color: white; padding: 20px 32px; }
        .header h1 { font-size: 24px; font-weight: 600; }
        .header p { font-size: 14px; opacity: 0.85; margin-top: 4px; }
        .chat-container { flex: 1; max-width: 900px; width: 100%; margin: 20px auto; padding: 0 16px; display: flex; flex-direction: column; gap: 16px; padding-bottom: 100px; }
        .message { padding: 16px 20px; border-radius: 12px; max-width: 85%; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .user-msg { background: #1a73e8; color: white; align-self: flex-end; border-bottom-right-radius: 4px; }
        .bot-msg { background: white; color: #1a1a1a; align-self: flex-start; border-bottom-left-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .sql-badge { background: #e8f0fe; color: #1a73e8; font-family: 'Courier New', monospace; font-size: 13px; padding: 8px 12px; border-radius: 6px; margin: 8px 0; display: block; word-break: break-all; }
        .results-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
        .results-table th { background: #f8f9fa; color: #1a73e8; padding: 10px 12px; text-align: left; border-bottom: 2px solid #e0e0e0; font-weight: 600; text-transform: uppercase; font-size: 12px; }
        .results-table td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }
        .results-table tr:hover td { background: #f8f9fa; }
        .input-bar { position: fixed; bottom: 0; left: 0; right: 0; background: white; padding: 16px; box-shadow: 0 -2px 10px rgba(0,0,0,0.1); }
        .input-wrapper { max-width: 900px; margin: 0 auto; display: flex; gap: 10px; }
        .input-wrapper input { flex: 1; padding: 14px 18px; border: 2px solid #e0e0e0; border-radius: 25px; font-size: 15px; outline: none; transition: border 0.2s; }
        .input-wrapper input:focus { border-color: #1a73e8; }
        .input-wrapper button { background: #1a73e8; color: white; border: none; padding: 14px 28px; border-radius: 25px; font-size: 15px; cursor: pointer; font-weight: 500; transition: background 0.2s; }
        .input-wrapper button:hover { background: #1557b0; }
        .input-wrapper button:disabled { background: #ccc; cursor: not-allowed; }
        .error { color: #d32f2f; font-weight: 500; }
        .welcome { text-align: center; padding: 40px 20px; color: #666; }
        .welcome h2 { color: #1a73e8; margin-bottom: 12px; }
        .suggestions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 16px; }
        .suggestions button { background: white; border: 1px solid #e0e0e0; padding: 8px 16px; border-radius: 20px; font-size: 13px; cursor: pointer; color: #333; transition: all 0.2s; }
        .suggestions button:hover { border-color: #1a73e8; color: #1a73e8; background: #e8f0fe; }
        .loader { display: inline-block; width: 20px; height: 20px; border: 2px solid #e0e0e0; border-top: 2px solid #1a73e8; border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="header">
        <h1>StartupIQ</h1>
        <p>Ask anything about Indian startup funding — powered by AlloyDB AI & Gemini</p>
    </div>
    <div class="chat-container" id="chat">
        <div class="welcome">
            <h2>Explore Indian Startup Data</h2>
            <p>Ask questions in plain English about 100+ Indian startups, their funding, investors, and more.</p>
            <div class="suggestions">
                <button onclick="askQuestion('Which are the top 5 most funded startups?')">Top 5 funded startups</button>
                <button onclick="askQuestion('How many startups are in Bangalore?')">Startups in Bangalore</button>
                <button onclick="askQuestion('Show me all fintech companies')">Fintech companies</button>
                <button onclick="askQuestion('Which startups are struggling?')">Struggling startups</button>
                <button onclick="askQuestion('What is the average funding by industry?')">Avg funding by industry</button>
            </div>
        </div>
    </div>
    <div class="input-bar">
        <div class="input-wrapper">
            <input type="text" id="query" placeholder="Ask about Indian startups..." onkeypress="if(event.key==='Enter')ask()">
            <button onclick="ask()" id="askBtn">Ask</button>
        </div>
    </div>
    <script>
        function askQuestion(q) { document.getElementById('query').value = q; ask(); }
        async function ask() {
            const input = document.getElementById('query');
            const btn = document.getElementById('askBtn');
            const q = input.value.trim();
            if (!q) return;
            const chat = document.getElementById('chat');
            if (chat.querySelector('.welcome')) chat.querySelector('.welcome').remove();
            chat.innerHTML += '<div class="message user-msg">' + q + '</div>';
            chat.innerHTML += '<div class="message bot-msg" id="loading"><div class="loader"></div> Thinking...</div>';
            input.value = '';
            btn.disabled = true;
            window.scrollTo(0, document.body.scrollHeight);
            try {
                const res = await fetch('/query', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question: q})
                });
                const data = await res.json();
                document.getElementById('loading').remove();
                if (data.error) {
                    chat.innerHTML += '<div class="message bot-msg"><span class="error">' + data.error + '</span></div>';
                } else {
                    let html = '<div class="message bot-msg">';
                    html += '<code class="sql-badge">' + data.sql + '</code>';
                    if (data.results && data.results.length > 0) {
                        html += '<table class="results-table"><thead><tr>';
                        Object.keys(data.results[0]).forEach(k => html += '<th>' + k.replace(/_/g, ' ') + '</th>');
                        html += '</tr></thead><tbody>';
                        data.results.forEach(row => {
                            html += '<tr>';
                            Object.values(row).forEach(v => html += '<td>' + (v !== null ? v : '-') + '</td>');
                            html += '</tr>';
                        });
                        html += '</tbody></table>';
                        html += '<p style="margin-top:8px;font-size:12px;color:#888;">' + data.results.length + ' result(s)</p>';
                    } else {
                        html += '<p>No results found.</p>';
                    }
                    html += '</div>';
                    chat.innerHTML += html;
                }
            } catch(e) {
                document.getElementById('loading').remove();
                chat.innerHTML += '<div class="message bot-msg"><span class="error">Something went wrong. Try again.</span></div>';
            }
            btn.disabled = false;
            window.scrollTo(0, document.body.scrollHeight);
        }
    </script>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)


@app.route("/query", methods=["POST"])
def query():
    data = request.get_json()
    question = data.get("question", "")

    if not question:
        return jsonify({"error": "Please provide a question"}), 400

    try:
        response = model.generate_content(SYSTEM_PROMPT + "\n\nQ: " + question + "\nA: ")
        sql = response.text.strip()
        sql = sql.replace("```sql", "").replace("```", "").strip()

        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"]
        for word in forbidden:
            if word in sql.upper().split()[0:3]:
                return jsonify({"error": "Only SELECT queries are allowed."}), 400

        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            for row in rows:
                for k, v in row.items():
                    if hasattr(v, '__float__'):
                        row[k] = float(v)

        return jsonify({"sql": sql, "results": rows})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
