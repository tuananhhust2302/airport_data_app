from flask import Flask, render_template, request, redirect, session, send_file
import json
import os
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = "foe_secret_key"

DATA_FILE = "data.json"

# =========================
# FIELD DEFINITION
# =========================

FIELDS = {
    "DOCUMENT": [
        "LIDO_mPilot",
        "EFB2",
        "EFB3",
        "EOSID_CHART",
        "EDTO_MANUAL",
        "ROUTE_MANUAL",
        "RTOW"
    ],
    "NAVIGATION_TERRAIN_DATA": [
        "VN4",
        "VN6",
        "VN7",
        "VN9",
        "HVN2",
        "TERRAIN",
        "EOSID_NAV"
    ],
    "AMM": [
        "AMM_EFB2",
        "AMM_EFB3",
        "AMM_AVIONIC",
        "AMM_mPILOT"
    ],
    "PROCEDURES": [
        "TAKE_OFF_LVP",
        "RNAV_SID_STAR",
        "ILS",
        "VOR",
        "RNP",
        "NDB",
        "EOSID_PROCEDURES"
    ],
    "AIRPORT_INFORMATION": [
        "AIRPORT_NAME",
        "CITY_NAME",
        "COUNTRY_NAME",
        "RUNWAY_LENGTH",
        "PCN_PCR",
        "RFFS_CAT",
        "FUEL",
        "OPERATING_HOUR"
    ]
}

# =========================
# DATA HANDLING
# =========================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "foe2026" and request.form["password"] == "foe2026":
            session["logged_in"] = True
            return redirect("/")
    return """
    <h2>FOE LOGIN</h2>
    <form method="post">
        Username:<br><input name="username"><br>
        Password:<br><input type="password" name="password"><br><br>
        <button type="submit">Login</button>
    </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# INPUT DATA (PRE-FILL)
# =========================

@app.route("/", methods=["GET", "POST"])
def input_data():

    if not session.get("logged_in"):
        return redirect("/login")

    data = load_data()

    selected_airport = request.args.get("airport", "").upper()
    loaded = {}

    # load nếu đã có dữ liệu
    if selected_airport and selected_airport in data:
        loaded = data[selected_airport]

    # SAVE
    if request.method == "POST":
        airport = request.form["airport"].upper()
        data[airport] = {}

        for group, items in FIELDS.items():
            for i in items:
                if group == "AIRPORT_INFORMATION":
                    data[airport][i] = request.form.get(i, "")
                else:
                    tick = 1 if request.form.get(i) else 0
                    note = request.form.get(i + "_note", "")
                    data[airport][i] = [tick, note]

        save_data(data)
        loaded = data[airport]
        selected_airport = airport

    return render_template(
        "input.html",
        fields=FIELDS,
        data=data,
        loaded=loaded,
        selected_airport=selected_airport
    )


# =========================
# CHECK DATA
# =========================

@app.route("/check", methods=["GET", "POST"])
def check_data():

    if not session.get("logged_in"):
        return redirect("/login")

    raw_data = load_data()
    result = {}

    if request.method == "POST":
        airports = [a.strip().upper() for a in request.form["airports"].split(",")]
        filters = request.form.getlist("filters")

        if not filters:
            filters = []
            for group in FIELDS.values():
                filters.extend(group)

        for a in airports:
            if a in raw_data:
                result[a] = {"CHECK": {}}
                for f in filters:
                    result[a]["CHECK"][f] = raw_data[a].get(f, [0, ""])

        session["last_check_airports"] = airports
        session["last_check_filters"] = filters

    return render_template("check.html", data=result, fields=FIELDS)


# =========================
# EXPORT EXCEL
# =========================

@app.route("/export", methods=["POST"])
def export_excel():

    if not session.get("logged_in"):
        return redirect("/login")

    raw_data = load_data()
    airports = session.get("last_check_airports", [])
    rows = []

    for a in airports:
        if a in raw_data:
            row = {"AIRPORT": a}

            for group, items in FIELDS.items():
                for f in items:
                    value = raw_data[a].get(f, "")
                    if group == "AIRPORT_INFORMATION":
                        row[f] = value
                    else:
                        row[f] = "YES" if isinstance(value, list) and value[0] == 1 else "NO"

            rows.append(row)

    df = pd.DataFrame(rows)

    filename = f"Airport_Check_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    df.to_excel(filename, index=False)

    return send_file(filename, as_attachment=True)


# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
