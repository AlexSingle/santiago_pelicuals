#!/usr/bin/env python3
"""
Fetches subtitled (SUB) cinema sessions for Santiago districts.
Output: JSON to stdout.
"""
import json, sys
import urllib.request, urllib.error
from datetime import date, datetime, timedelta
from collections import defaultdict

TITLE_MAP = {
    "El Diablo Viste A La Moda 2":                       "The Devil Wears Prada 2",
    "El Drama":                                           "The Drama",
    "Proyecto Fin Del Mundo":                             "Project Hail Mary",
    "La Posesion De La Momia":                           "The Mummy",
    "La Posesión De La Momia":                          "The Mummy",
    "Slime: Lagrimas Del Mar Celeste":                   "That Time I Got Reincarnated as a Slime",
    "Slime: Lágrimas Del Mar Celeste":                  "That Time I Got Reincarnated as a Slime",
    "Slime 2":                                           "That Time I Got Reincarnated as a Slime",
    "Super Mario Galaxy: La Pelicula":                   "Super Mario Galaxy: The Movie",
    "Super Mario Galaxy: La Película":                  "Super Mario Galaxy: The Movie",
    "El Vengador Toxico":                                "The Toxic Avenger",
    "El Vengador Tóxico":                               "The Toxic Avenger",
}

def translate_title(title):
    return TITLE_MAP.get(title, title)

CINEMARK_URL  = "https://bff.cinemark.cl/api/cinema/showtimes?theater={}"
CINEMARK_HDRS = {"country":"CL","Accept":"application/json","Origin":"https://www.cinemark.cl","User-Agent":"Mozilla/5.0"}

CP_SESSIONS_URL = "https://www.cineplanet.cl/v3/api/cache/sessioncache"
CP_MOVIES_URL   = "https://www.cineplanet.cl/v3/api/cache/moviescache"
CP_HDRS = {
    "Ocp-Apim-Subscription-Key": "c6f97c336b60469189a010a5836fe891",
    "Authorization": "Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ3ZWJ1c2VyIiwiYXV0aCI6IlJPTEVfVVNFUiIsImV4cCI6NDg3MDQ0OTgyOX0.xLze7Vba9aNRv-dEetE4GTKVI1qWBaXTaeMpTZBiy0H6yOBEvEsnmbLGoShpuGe1Ok_6o8TmacBsYANimEu6rQ",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}

CP_HOYTS_URL  = "https://cinepolischile.cl/Cartelera.aspx/GetNowPlayingByCity"
CP_HOYTS_HDRS = {
    "Content-Type":"application/json; charset=utf-8",
    "Accept":"application/json, text/javascript, */*; q=0.01",
    "Origin":"https://cinepolischile.cl",
    "Referer":"https://cinepolischile.cl/cartelera/santiago-oriente/",
    "User-Agent":"Mozilla/5.0",
    "X-Requested-With":"XMLHttpRequest",
}

CINEMAS = [
    {"name":"Cinemark Alto Las Condes",         "district":"Las Condes",  "source":"cinemark",  "theater_id":"512"},
    {"name":"Cinemark Portal Nuñoa",            "district":"Ñuñoa",       "source":"cinemark",  "theater_id":"2300"},
    {"name":"Cineplanet Costanera",             "district":"Providencia", "source":"cineplanet","cinema_id":"0000000004"},
    {"name":"Cinepolis Parque Arauco",          "district":"Las Condes",  "source":"cinepolis", "city_key":"santiago-oriente","cinema_slug":"parque-arauco"},
    {"name":"Cinepolis Mallplaza Egana",        "district":"Ñuñoa",       "source":"cinepolis", "city_key":"santiago-oriente","cinema_slug":"cinepolis-mallplaza-egana"},
    {"name":"Cinepolis Mallplaza Los Dominicos","district":"Las Condes",  "source":"cinepolis", "city_key":"santiago-oriente","cinema_slug":"cinepolis-mallplaza-los-dominicos"},
    {"name":"Cinepolis Casa Costanera",         "district":"Vitacura",    "source":"cinepolis", "city_key":"santiago-oriente","cinema_slug":"cinepolis-casa-costanera"},
    {"name":"Cinepolis La Reina",               "district":"La Reina",    "source":"cinepolis", "city_key":"santiago-oriente","cinema_slug":"cinepolis-la-reina"},
    {"name":"Cinepolis Parque Arauco VIP",       "district":"Las Condes",  "source":"cinepolis", "city_key":"santiago-oriente","cinema_slug":"parque-arauco-premium-class"},
    {"name":"Cinepolis Mallplaza Egana VIP",     "district":"Ñuñoa",       "source":"cinepolis", "city_key":"santiago-oriente","cinema_slug":"cinepolis-mallplaza-egana-premium-class"},
    {"name":"Cinepolis Los Dominicos VIP",       "district":"Las Condes",  "source":"cinepolis", "city_key":"santiago-oriente","cinema_slug":"cinepolis-mallplaza-los-dominicos-premium-class"},
]

def date_range():
    today = date.today()
    days_to_wed = (2 - today.weekday()) % 7
    end = today + timedelta(days=days_to_wed if days_to_wed > 0 else 0)
    return today, end

def fetch(url, headers, data=None):
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def day_label(d_str):
    d = date.fromisoformat(d_str)
    days   = ["Lunes","Martes","Miercoles","Jueves","Viernes","Sabado","Domingo"]
    months = ["","enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
    return f"{days[d.weekday()]} {d.day} de {months[d.month]}"

def fetch_cinemark(theater_id, start, end):
    data     = fetch(CINEMARK_URL.format(theater_id), CINEMARK_HDRS)
    sessions = data.get("data", [])
    by_date  = defaultdict(lambda: defaultdict(list))
    for s in sessions:
        if s.get("language", {}).get("shortName") != "SUB":
            continue
        sd_str = s.get("sessionDisplayDate", "")
        if not sd_str:
            continue
        sd = date.fromisoformat(sd_str)
        if not (start <= sd <= end):
            continue
        movie = translate_title(s.get("movieName", "?").title())
        dt    = s.get("sessionDateTime", "")
        time  = dt[11:16] if len(dt) >= 16 else "?"
        fmt   = s.get("sessionFormat", "")
        by_date[sd_str][movie].append({"time": time, "format": fmt})
    return by_date

def fetch_cineplanet(cinema_id, start, end):
    sessions_raw = fetch(CP_SESSIONS_URL, CP_HDRS).get("sessions", [])
    movies_raw   = fetch(CP_MOVIES_URL, CP_HDRS).get("movies", [])
    sid_to_title = {}
    for m in movies_raw:
        for c in m.get("cinemas", []):
            for day in c.get("dates", []):
                for sid in day.get("sessions", []):
                    sid_to_title[sid] = translate_title(m["title"].strip().title())
    by_date = defaultdict(lambda: defaultdict(list))
    for s in sessions_raw:
        sid = s["id"]
        if not sid.startswith(cinema_id + "-"):
            continue
        if "SUBTITULAD" not in s.get("languages", []):
            continue
        showtime_str = s.get("showtime", "")
        if not showtime_str:
            continue
        dt  = datetime.fromisoformat(showtime_str)
        sd  = dt.date()
        if not (start <= sd <= end):
            continue
        time  = dt.strftime("%H:%M")
        fmt   = "+".join(s.get("formats", []))
        movie = sid_to_title.get(sid, "Unknown")
        by_date[sd.isoformat()][movie].append({"time": time, "format": fmt})
    return by_date

def fetch_cinepolis(city_key, cinema_slug, start, end):
    payload   = json.dumps({"claveCiudad": city_key, "esVIP": False}).encode("utf-8")
    resp      = fetch(CP_HOYTS_URL, CP_HOYTS_HDRS, data=payload)
    city_data = resp.get("d") or {}
    cinemas   = city_data.get("Cinemas") or []
    by_date   = defaultdict(lambda: defaultdict(list))
    for cinema in cinemas:
        if cinema.get("Key", "").lower() != cinema_slug.lower():
            continue
        for day in (cinema.get("Dates") or []):
            filter_date = day.get("FilterDate", "")
            try:
                ms = int(filter_date.replace("/Date(", "").replace(")/", ""))
                sd = datetime.utcfromtimestamp(ms / 1000).date()
            except Exception:
                continue
            if not (start <= sd <= end):
                continue
            for movie in (day.get("Movies") or []):
                raw_title = (movie.get("OriginalTitle") or movie.get("Title") or "?").strip()
                title = translate_title(raw_title.title())
                for fmt in (movie.get("Formats") or []):
                    lang     = fmt.get("Language", "")
                    fmt_name = fmt.get("Name", "")
                    if "SUBTITULAD" not in lang.upper() and "ORI" not in lang.upper():
                        continue
                    for showtime in (fmt.get("Showtimes") or []):
                        t = showtime.get("Time") or "?"
                        by_date[sd.isoformat()][title].append({"time": t, "format": fmt_name})
    return by_date

def main():
    start, end = date_range()
    result = {
        "range_start": start.isoformat(),
        "range_end":   end.isoformat(),
        "fetched_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "cinemas": [],
    }
    for cinema in CINEMAS:
        error = None
        try:
            if cinema["source"] == "cinemark":
                by_date = fetch_cinemark(cinema["theater_id"], start, end)
            elif cinema["source"] == "cineplanet":
                by_date = fetch_cineplanet(cinema["cinema_id"], start, end)
            elif cinema["source"] == "cinepolis":
                by_date = fetch_cinepolis(cinema["city_key"], cinema["cinema_slug"], start, end)
            else:
                by_date = {}
                error = "Unknown source"
        except Exception as e:
            by_date = {}
            error   = str(e)
        days_out = []
        for d_str in sorted(by_date.keys()):
            movies_out = []
            for title in sorted(by_date[d_str].keys()):
                showtimes = sorted(by_date[d_str][title], key=lambda x: x["time"])
                movies_out.append({"title": title, "showtimes": showtimes})
            days_out.append({"date": d_str, "label": day_label(d_str), "movies": movies_out})
        result["cinemas"].append({
            "name":     cinema["name"],
            "district": cinema["district"],
            "days":     days_out,
            "error":    error,
        })
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
