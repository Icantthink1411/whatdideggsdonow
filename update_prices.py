#!/usr/bin/env python3
"""
whatdideggsdonow.com — Weekly Price Updater
============================================
Fetches the latest prices from the FRED API and updates index.html.
Snark is randomly selected from a pool each run, so the site feels fresh every week.

SETUP:
  pip install requests

USAGE:
  python update_prices.py --key YOUR_FRED_API_KEY

SCHEDULE (run every Sunday):
  Mac/Linux cron:  0 8 * * 0 cd /path/to/site && python update_prices.py --key YOUR_KEY
  Windows Task Scheduler: point at this script, run weekly on Sunday

NOTE:
  Most BLS price series (APU) update monthly. Gas and diesel (GASREGW, GASDESW)
  update weekly. The script always uses the most recent available data point.

ADDING NEW SNARK:
  Each item has a "snark" dict with "up", "down", and "flat" lists.
  Just add new strings to any list — the script picks one at random each run.
"""

import argparse
import json
import random
import re
import sys
import time
import requests
from datetime import datetime, timedelta

# ── Series definitions ────────────────────────────────────────────────────────

SERIES = [
    {
        "id": "eggs", "name": "Eggs", "unit": "1 dozen, Grade A Large", "emoji": "🥚",
        "fred_id": "APU0000708111", "multiplier": 1.0,
        "snark": {
            "up": [
                "The chickens raised their rates again. They have no union, no oversight, and apparently no shame.",
                "Eggs up again. At this point the chickens are running a cartel and the government is doing nothing about it.",
                "Another week, another assault on your breakfast budget. The hens remain smug and unreachable.",
                "Up again. The egg is now a luxury item. The egg. We have failed as a civilization.",
                "Eggs cost more than last week. The chickens were asked for comment. The chickens laid another egg and charged us for it.",
                "Price up. The birds have looked at your grocery budget, assessed the situation, and chosen violence.",
                "Another hike. Scientists are studying the chicken. The chicken does not care. The chicken has already cashed out.",
            ],
            "down": [
                "Eggs dropped this week. The chickens blinked. Don't let them see you celebrating or they'll take it back.",
                "Down slightly. Whether this is mercy or a trap remains unclear. Stock up quietly.",
                "A brief ceasefire in the egg wars. Enjoy the savings. Say nothing. Make no sudden movements.",
                "Eggs went down. Write this date in your calendar. Frame it. Cry a little. You've earned it.",
                "The chickens had a moment of weakness. Exploit it immediately. Buy everything. Tell no one.",
                "Price dropped. We don't know why and frankly we're afraid to ask.",
                "Down this week. The egg is briefly affordable. This sentence has never felt more absurd to type.",
            ],
            "flat": [
                "Holding steady. The chickens are watching. Stay calm. Do not make eye contact.",
                "No change. The egg market has chosen psychological warfare over direct price hikes this week.",
                "Flat. This is either a rest day or the buildup to something terrible. Historically, it's the latter.",
                "Eggs unchanged. Somewhere a chicken is planning something. We just don't know what yet.",
                "Steady. The hens are in a neutral arc. This is the most unsettling thing they've ever done.",
                "No movement this week. The calm before the carton.",
            ],
        }
    },
    {
        "id": "milk", "name": "Milk", "unit": "1 gallon, whole", "emoji": "🥛",
        "fred_id": "APU0000709112", "multiplier": 1.0,
        "snark": {
            "up": [
                "The cows have seen what the chickens are getting away with and they want a piece of it.",
                "Milk up. The cows attended the chickens' pricing seminar, took detailed notes, and implemented immediately.",
                "Up this week. Even milk. MILK. The beige wallpaper of groceries. Even that is doing this now.",
                "Milk went up. At some point a bowl of cereal becomes a financial decision and that point is now.",
                "The cows are not sorry. The cows have never been sorry. The cows will never be sorry.",
                "Up again. The dairy industry looked at your pantry, calculated exactly what you need, and raised the price.",
                "More expensive this week. The cows have secured representation. The cows are eating well.",
            ],
            "down": [
                "Milk went down. We don't trust it but we're not in a position to be picky right now.",
                "Down slightly. The cows are feeling generous. Something is wrong with the cows but we're taking the deal.",
                "Dropped a bit. A quiet win. A suspicious win. But a win.",
                "Went down a bit. The cows and the chickens are clearly not coordinating. Good. Let them fight.",
                "Milk is cheaper this week. Pour the cereal. Don't ask questions.",
                "Down. In this economy? Yes. Enjoy it before someone notices.",
            ],
            "flat": [
                "Holding steady. The cows are in an unreadable mood. The cows are always in an unreadable mood.",
                "No change. Milk is the most stable thing in your life right now. Sit with that.",
                "Flat. The cows issued no statement and we respect the professionalism of that.",
                "Unchanged. Milk is holding it together while everything else falls apart. Milk is the adult in the room.",
                "Steady. The dairy sector has chosen stillness. We appreciate it. We don't trust it.",
            ],
        }
    },
    {
        "id": "butter", "name": "Butter", "unit": "1 lb, salted", "emoji": "🧈",
        "fred_id": "APU0000FS1101", "multiplier": 1.0,
        "snark": {
            "up": [
                "Butter up again. Toast is a luxury item now. Act accordingly and grieve accordingly.",
                "Up this week. Every recipe that starts with 'melt two tablespoons of butter' is now a financial commitment.",
                "Butter went up. The French are furious on our behalf and honestly we need their energy right now.",
                "More expensive this week. Butter has fully transitioned from staple to splurge and it feels great about that.",
                "Up again. We are one more price hike away from dry toast and quiet suffering and that is not a joke.",
                "Butter costs more. The audacity of a dairy product to do this to us is genuinely staggering.",
                "Up. The stick of butter has decided it's a luxury good. The stick of butter is winning.",
            ],
            "down": [
                "Butter dipped. We remain cautiously optimistic, deeply suspicious, and ready for this to reverse immediately.",
                "Down slightly. The croissant is briefly within reach. The biscuit has returned to us.",
                "Butter went down. A small mercy for anyone who has been eyeing that cookie recipe and doing math.",
                "Dropped a bit. The toast economy shows signs of recovery. We are cautiously toasting.",
                "Down this week. Someone in the dairy supply chain did something right. We'd like to thank them personally.",
                "Butter came down. Cook everything. Do it now before it changes its mind.",
            ],
            "flat": [
                "Butter is holding steady. The most suspenseful thing butter has ever done in its entire life.",
                "No change. Butter has decided to simply exist this week without drama. We don't know this butter.",
                "Flat. Butter is not escalating. This is so out of character we're a little concerned.",
                "Unchanged. Butter is doing its job and nothing else. Finally. Finally the professionalism we deserved.",
                "Holding. The bread and butter relationship remains intact. For now. Check back Sunday.",
            ],
        }
    },
    {
        "id": "bread", "name": "Bread", "unit": "1 loaf, white sandwich", "emoji": "🍞",
        "fred_id": "APU0000702111", "multiplier": 1.25,
        "snark": {
            "up": [
                "Bread went up. BREAD. The food of the people. The last refuge. Bread has betrayed us.",
                "Up this week. If bread is getting expensive, we are genuinely out of options and that's the column.",
                "Even bread is doing this now. Even bread. We need a moment.",
                "Bread costs more this week. A sandwich is now an investment. Pack your lunch with intention.",
                "Up again. At some point toast becomes a treat. We are so close to that point. We are almost there.",
                "More expensive. The loaf has looked at the economic climate and decided to participate. Awful.",
                "Bread went up. This is the grocery equivalent of the floor falling out. We're in the basement now.",
            ],
            "down": [
                "Bread went down. The hero we needed. The hero we don't deserve. Bread has chosen the people.",
                "Down slightly. The loaf remains accessible. The sandwich endures. We live to eat another day.",
                "Went down a little. Bread is doing the work that everything else refuses to do. Legend.",
                "Bread dipped. In a brutal week for groceries, bread said 'not today' and meant it.",
                "Down this week. Bread remains the people's carb. Bread shows up. Bread cares.",
                "Cheaper this week. Make a sandwich. Make two. Make a sandwich tower and call it dinner.",
            ],
            "flat": [
                "Bread is stable. Bless bread. Bread is fine. Bread is the only thing that is fine.",
                "No change. Bread is holding the line while everything around it turns to chaos. Bread is us.",
                "Flat. Bread is not making headlines. This is the greatest compliment bread has ever received.",
                "Unchanged. Bread is steady. Bread is reliable. Bread is there for you. Bread gets it.",
                "Holding. The loaf endures. We endure. Together.",
            ],
        }
    },
    {
        "id": "beef", "name": "Ground Beef", "unit": "1 lb, 80/20", "emoji": "🥩",
        "fred_id": "APU0000703112", "multiplier": 1.0,
        "snark": {
            "up": [
                "Ground beef up again. A burger is now officially a treat and Taco Tuesday needs a line item.",
                "Up this week. The dream of a cheap weeknight dinner is retreating so fast we can barely see it.",
                "Went up. The backyard grill is becoming a financial commitment we need to sit down and discuss.",
                "More expensive this week. Ground beef has decided it's a premium product. It is wrong but it is winning.",
                "Up again. At this price, spaghetti night is a luxury experience. We hate it here.",
                "Costs more. The cow is doing this deliberately and we have no way to prove it but we know.",
                "Another hike. The humble burger patty has gotten above itself and frankly the audacity is impressive.",
            ],
            "down": [
                "Beef came down. The grill is calling. The taco is calling. Everything is calling. Go.",
                "Down slightly. Make the burgers. Make the meatballs. Make the Bolognese. Do it right now.",
                "Went down. Taco Tuesday is back on the table, literally and financially.",
                "Beef dipped. A rare and beautiful win for people who just want a normal, affordable dinner.",
                "Down this week. We repeat: the beef is down. Drop what you're doing. Go to the store.",
                "Cheaper this week. Cook something that requires a pound of ground beef and feel genuinely good about it.",
            ],
            "flat": [
                "Ground beef unchanged. The cows are holding the line. The cows have made their position clear.",
                "No change. The beef market is doing nothing and somehow that is the best news in the section.",
                "Flat. Ground beef locked in. We will not jinx this by talking about it further.",
                "Unchanged this week. The hamburger economy is stable. Do not touch it. Do not look at it. Just eat it.",
                "Holding. The cow situation remains unresolved but at least the price is consistent. That's something.",
            ],
        }
    },
    {
        "id": "chicken", "name": "Chicken Breast", "unit": "1 lb, boneless skinless", "emoji": "🍗",
        "fred_id": "APU0000FF1101", "multiplier": 1.0,
        "snark": {
            "up": [
                "The chickens got agents and a publicist. Rates went up. We're all paying for the rebrand.",
                "Up this week. Chicken is aggressively auditioning for the role of luxury protein and it's booking the part.",
                "Went up. The last affordable protein has looked at your budget and decided to stop being affordable.",
                "More expensive this week. Chicken has attended the egg meetings and the egg meetings have corrupted it.",
                "Up again. The poultry industrial complex has tightened its grip and it is not releasing.",
                "Chicken costs more. The bird that was supposed to save us has joined the enemy. Stunning betrayal.",
                "Higher this week. At some point chicken breast becomes a special occasion protein. We are there.",
            ],
            "down": [
                "Chicken down. The last affordable protein lives another week. The people cheer. Quietly.",
                "Down a bit. Chicken remains the sensible choice and has earned every ounce of our loyalty.",
                "Went down. The budget dinner survives. Make the stir fry. Make the soup. Make it all.",
                "Dropped slightly. Chicken is out here doing the work that beef and fish refuse to do. A hero.",
                "Down this week. The responsible protein is rewarding your loyalty and we love to see it.",
                "Cheaper this week. Chicken shows up. Chicken delivers. Chicken is the dependable friend we needed.",
            ],
            "flat": [
                "Chicken holding steady. The budget protein maintains its dignity in a world that has none.",
                "No change. Chicken continues to be dependable in a deeply undependable economy. A true ally.",
                "Flat. Chicken is just showing up and doing its job without drama. We could all learn from chicken.",
                "Unchanged. In a world of chaos, chicken is stable. Chicken is enough. Chicken is all we have.",
                "Holding. Chicken is not making things worse. At this particular moment in history, that is heroic.",
            ],
        }
    },
    {
        "id": "bacon", "name": "Bacon", "unit": "1 lb, sliced", "emoji": "🥓",
        "fred_id": "APU0000704111", "multiplier": 1.0,
        "snark": {
            "up": [
                "Bacon up again. The weekend breakfast that used to be a given is now a calculated indulgence.",
                "Up this week. Saturday morning has officially become an expensive hobby.",
                "Went up. BLT season is in active jeopardy. The lettuce and tomato are fine. It's the bacon.",
                "More expensive this week. Bacon has decided it's a treat and it has never been more correct.",
                "Up again. The pigs have secured representation and their first demand was this. Bold move.",
                "Higher this week. At some point bacon becomes a special occasion food and that occasion is apparently right now.",
                "Up. Breakfast is now fine dining and no one asked for that transition but here we are.",
            ],
            "down": [
                "Bacon came down. The weekend got better. Everything is better. Fry something immediately.",
                "Down slightly. The BLT has been restored. The breakfast sandwich is back. Justice has been served.",
                "Went down. This is what good news feels like. Remember this. Screenshot it. Tell someone.",
                "Bacon dipped. Treat yourself. You have been through a lot and the bacon is cheaper. Go.",
                "Down this week. The breakfast situation is improving. Don't get used to it but do enjoy it.",
                "Cheaper this week. Make the bacon. Make it all. Eat it standing over the stove. You earned this.",
            ],
            "flat": [
                "Bacon holding steady. The pan is ready. The price is stable. The weekend is happening. Go.",
                "No change. Bacon remains expensive and completely worth every cent. Some things are sacred.",
                "Flat. Bacon is not escalating this week. We would like to formally thank bacon for its restraint.",
                "Unchanged. Bacon holds its price like it holds its flavor — stubbornly and with no apologies.",
                "Holding. The bacon market is stable. Cook some. You deserve it. That is not financial advice.",
            ],
        }
    },
    {
        "id": "coffee", "name": "Coffee", "unit": "1 lb, ground roast", "emoji": "☕",
        "fred_id": "APU0000717311", "multiplier": 1.0,
        "snark": {
            "up": [
                "Coffee up again. The one thing keeping us functional is now also the thing destroying our finances.",
                "Up this week. The morning ritual is now a luxury experience and we didn't consent to that upgrade.",
                "Went up. Making coffee at home was supposed to be the affordable option. That option is now also unaffordable.",
                "More expensive this week. The beans have looked at the economy and decided to make it worse. Cool.",
                "Up again. We are drinking our feelings and our feelings now cost more than they did last week.",
                "Higher this week. The coffee supply chain has decided that functioning adults should pay a premium for functioning.",
                "Up. Cutting out the daily latte was supposed to fix this. It has not fixed this. Nothing has fixed this.",
            ],
            "down": [
                "Coffee dropped. The universe is offering you one small mercy. Accept it. Do not question it.",
                "Down a bit. The morning is briefly affordable. Brew an extra cup. You've genuinely earned it.",
                "Went down. Drink up. This won't last and we all know it so just drink up and say nothing.",
                "Dropped slightly. The coffee supply chain did something right for once and we're almost moved.",
                "Down this week. Start the morning correctly. Prices cooperated. Everything is fine for now.",
                "Cheaper this week. Make a full pot. Drink it luxuriously. Tell the beans we appreciate them.",
            ],
            "flat": [
                "Coffee is flat. Which is more than can be said for our entire mood without it.",
                "No change. Coffee is holding. So are we. Barely, technically, but we're holding.",
                "Flat. The beans are in a neutral arc. The mug is full. This is as good as things get.",
                "Unchanged. Coffee didn't get more expensive this week. That's the bar now and we cleared it.",
                "Holding. The coffee is fine. Everything else is unraveling but the coffee is fine.",
            ],
        }
    },
    {
        "id": "oj", "name": "Orange Juice", "unit": "16 oz, frozen concentrate", "emoji": "🍊",
        "fred_id": "APU0000713111", "multiplier": 1.0,
        "snark": {
            "up": [
                "OJ up again. You are not drinking orange juice. You are drinking Florida real estate. Pulp free.",
                "Up this week. Orange juice has fully committed to being a luxury beverage and it is pulling it off effortlessly.",
                "Went up. The orange situation continues to be a situation and the situation is getting worse.",
                "More expensive this week. At some point OJ becomes a special occasion drink and we have reached that point.",
                "Up again. The citrus market is doing something dramatic and none of it is in our interest.",
                "Higher. Vitamin C is now a splurge and we are one bad harvest away from eating the orange peel for efficiency.",
                "Up. OJ has looked at the egg prices and thought 'yes, I want that energy.' Devastating.",
            ],
            "down": [
                "Orange juice dropped. Still expensive. Still absolutely worth it. Pour a full glass. You deserve it.",
                "Down a bit. The morning glass of OJ is briefly accessible again. Florida has chosen grace.",
                "Went down. Someone had a good harvest and made a good decision and we are grateful beyond words.",
                "Dropped slightly. The orange gave back a little. Take it. Squeeze the moment.",
                "Down this week. OJ is briefly reasonable. This is temporary but it is real and we are drinking it.",
                "Cheaper this week. The citrus situation improved. Add it to the extremely short list of things that improved.",
            ],
            "flat": [
                "OJ is flat. A small mercy in a citrus market that has shown us absolutely no mercy.",
                "No change. Orange juice is holding. Your breakfast budget is holding. Everything is fine.",
                "Flat. The orange market has entered a quiet period. We are respecting the quiet period.",
                "Unchanged. OJ doing nothing dramatic this week. For OJ, in this economy, that IS dramatic.",
                "Holding. The citrus holds. We hold. We go on. That's the whole thing. We just go on.",
            ],
        }
    },
    {
        "id": "gas", "name": "Regular Gas", "unit": "1 gallon", "emoji": "⛽",
        "fred_id": "GASREGW", "multiplier": 1.0,
        "snark": {
            "up": [
                "Gas up. You are now paying more to drive to the store to witness all the other price increases. Gorgeous.",
                "Up this week. The commute is more expensive. The errand is more expensive. Existing is more expensive.",
                "Went up. Everything you buy arrived on a truck. The truck noticed. The truck is billing accordingly.",
                "More expensive this week. The pump has assessed your situation and decided it could be worse. It made it worse.",
                "Up again. Fill up on a Tuesday if you can. It won't save much but at this point we take every inch.",
                "Higher this week. The gas station is the first punch of a grocery run that keeps punching the whole time.",
                "Up. The petroleum market looked at your budget and saw room to grow. There was no room. They grew anyway.",
            ],
            "down": [
                "Gas down slightly. You saved approximately eleven cents. Go absolutely wild with your savings.",
                "Down a bit. Drive somewhere. Anywhere. The cost of getting there briefly got less offensive.",
                "Went down. A small rebate from the universe for putting up with absolutely all of this.",
                "Dropped slightly. The pump is cooperative this week. Write the date down. This is notable.",
                "Down this week. The commute is marginally less painful. We celebrate every marginal thing we can.",
                "Cheaper this week. Fill the tank. Do it without looking at the total. You've earned the ignorance.",
            ],
            "flat": [
                "Gas is flat. The pump is in a neutral mood. The pump is the most mentally stable thing in our lives.",
                "No change. Gas is holding. Your wallet is exactly as bad as it was. A lateral move.",
                "Flat. The gas price has chosen stillness. In this economy, stillness is a form of kindness.",
                "Unchanged. Gas didn't go up this week. Given the track record, this absolutely counts as good news.",
                "Holding. The pump asks nothing new of you this week. An unexpected gift. A rare grace.",
            ],
        }
    },
    {
        "id": "diesel", "name": "Diesel", "unit": "1 gallon", "emoji": "🚛",
        "fred_id": "GASDESW", "multiplier": 1.0,
        "snark": {
            "up": [
                "Diesel up. Everything you buy arrived on a truck. That truck now costs more to run. You'll be paying for that.",
                "Up this week. The supply chain is about to feel this and then you're about to feel the supply chain feeling it.",
                "Went up. When diesel rises, everything rises. It just takes a few weeks to show up on the shelf looking innocent.",
                "More expensive this week. The trucks are not happy. The trucks have nowhere to put their feelings except your receipt.",
                "Up again. Somewhere a logistics manager is on the phone and the person on the other end is also on hold.",
                "Higher. Diesel doesn't make headlines but diesel makes everything. And right now diesel costs more.",
                "Up. The trucking industry has sent a message. The message is arriving on a truck. The truck is expensive.",
            ],
            "down": [
                "Diesel down. A rare moment of trickle-down economics where something actually trickled in the right direction.",
                "Down slightly. The trucks are briefly content. This may eventually show up as lower grocery prices. Maybe.",
                "Went down. The supply chain is catching a break. That break will reach you eventually through a complex series of tubes.",
                "Dropped slightly. When diesel drops, hope springs. Slowly. Through a seventeen-step logistics network.",
                "Down this week. The trucking industry exhales. We exhale. Everything exhales. Something is going right.",
                "Cheaper this week. The downstream effects take weeks to land but they're coming and they're going to feel okay.",
            ],
            "flat": [
                "Diesel flat. The trucks are content. For now. The trucks are never content for long.",
                "No change. Diesel is holding. The supply chain is holding. The groceries are arriving. The cycle continues.",
                "Flat. The diesel market has made peace with itself this week. We respect the therapy it's clearly doing.",
                "Unchanged. The trucks roll on. The prices hold. The groceries arrive. This is fine. This is all fine.",
                "Holding. Diesel flat means nothing got worse upstream. That's the whole win and we're taking it.",
            ],
        }
    },
]

# ── Fallback values (used if FRED fetch fails) ────────────────────────────────
FALLBACKS = {
    "eggs":     {"current": 5.99,  "previous": 6.49,  "yearAgo": 3.29,  "history": [3.29, 3.89, 4.49, 5.19, 6.49, 5.99]},
    "milk":     {"current": 3.89,  "previous": 3.79,  "yearAgo": 3.49,  "history": [3.49, 3.55, 3.60, 3.69, 3.79, 3.89]},
    "butter":   {"current": 5.49,  "previous": 5.49,  "yearAgo": 4.19,  "history": [4.19, 4.55, 4.89, 5.19, 5.49, 5.49]},
    "bread":    {"current": 3.19,  "previous": 3.29,  "yearAgo": 2.79,  "history": [2.79, 2.89, 3.09, 3.29, 3.29, 3.19]},
    "beef":     {"current": 5.79,  "previous": 5.49,  "yearAgo": 4.89,  "history": [4.89, 4.99, 5.19, 5.39, 5.49, 5.79]},
    "chicken":  {"current": 4.29,  "previous": 3.99,  "yearAgo": 3.49,  "history": [3.49, 3.59, 3.79, 3.89, 3.99, 4.29]},
    "bacon":    {"current": 7.29,  "previous": 7.09,  "yearAgo": 6.49,  "history": [6.49, 6.69, 6.89, 7.09, 7.09, 7.29]},
    "coffee":   {"current": 7.49,  "previous": 6.99,  "yearAgo": 5.99,  "history": [5.99, 6.29, 6.59, 6.89, 6.99, 7.49]},
    "oj":       {"current": 6.49,  "previous": 5.99,  "yearAgo": 4.49,  "history": [4.49, 4.99, 5.49, 5.79, 5.99, 6.49]},
    "gas":      {"current": 3.14,  "previous": 3.25,  "yearAgo": 3.45,  "history": [3.45, 3.38, 3.20, 3.10, 3.25, 3.14]},
    "diesel":   {"current": 3.58,  "previous": 3.72,  "yearAgo": 3.89,  "history": [3.89, 3.80, 3.65, 3.55, 3.72, 3.58]},
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def trend(current, previous):
    diff = current - previous
    if abs(diff) / max(previous, 0.01) < 0.005:
        return "flat"
    return "up" if diff > 0 else "down"


def pick_snark(series_config, direction):
    """Randomly pick a snark line for the given direction."""
    return random.choice(series_config["snark"][direction])


def fetch_observations(fred_id, api_key, limit=80):
    """Fetch the most recent `limit` observations from FRED."""
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={fred_id}&api_key={api_key}"
        f"&sort_order=desc&limit={limit}&file_type=json"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return [o for o in data["observations"] if o["value"] not in (".", "")]


def get_year_ago_value(observations, current_date_str, multiplier):
    """Find the observation closest to one year before current_date_str."""
    target = datetime.strptime(current_date_str, "%Y-%m-%d") - timedelta(days=365)
    valid = [(datetime.strptime(o["date"], "%Y-%m-%d"), float(o["value"])) for o in observations]
    if not valid:
        return None
    closest_date, closest_val = min(valid, key=lambda x: abs((x[0] - target).days))
    return round(closest_val * multiplier, 2)


def fetch_item(series_config, api_key):
    """Fetch and return a price item dict from FRED."""
    fred_id = series_config["fred_id"]
    multiplier = series_config["multiplier"] or 1.0

    print(f"  Fetching {series_config['name']:<20}", end="")

    try:
        obs = fetch_observations(fred_id, api_key, limit=80)
        if len(obs) < 2:
            raise ValueError("Not enough observations returned")

        current  = round(float(obs[0]["value"]) * multiplier, 2)
        previous = round(float(obs[1]["value"]) * multiplier, 2)
        year_ago = get_year_ago_value(obs, obs[0]["date"], multiplier)
        history  = [round(float(o["value"]) * multiplier, 2) for o in reversed(obs[:6])]

        t = trend(current, previous)
        snark = pick_snark(series_config, t)

        print(f"${current:>6.2f}  ({'+' if current >= previous else ''}{((current-previous)/previous*100):.1f}%)")

        return {
            "id": series_config["id"],
            "name": series_config["name"],
            "unit": series_config["unit"],
            "emoji": series_config["emoji"],
            "current": current,
            "previous": previous,
            "yearAgo": year_ago or FALLBACKS[series_config["id"]]["yearAgo"],
            "history": history,
            "snark": snark,
        }

    except Exception as e:
        print(f"FAILED ({e}) — using fallback")
        fb = FALLBACKS[series_config["id"]]
        t = trend(fb["current"], fb["previous"])
        return {
            "id": series_config["id"],
            "name": series_config["name"],
            "unit": series_config["unit"],
            "emoji": series_config["emoji"],
            "current": fb["current"],
            "previous": fb["previous"],
            "yearAgo": fb["yearAgo"],
            "history": fb["history"],
            "snark": pick_snark(series_config, t),
        }


def format_week(dt):
    """Format date as 'May 4, 2026' without leading zero (cross-platform)."""
    return dt.strftime("%B {day}, %Y").replace("{day}", str(dt.day))


def update_html(html_path, items, week_str):
    """Replace FALLBACK_WEEK and FALLBACK_ITEMS in index.html."""
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Update FALLBACK_WEEK
    html = re.sub(
        r'const FALLBACK_WEEK = "[^"]+";',
        f'const FALLBACK_WEEK = "{week_str}";',
        html
    )

    # Build new FALLBACK_ITEMS JS block
    lines = ["const FALLBACK_ITEMS = ["]
    for item in items:
        history_str = ", ".join(str(h) for h in item["history"])
        snark_escaped = item["snark"].replace('"', '\\"')
        lines.append(
            f'  {{\n'
            f'    id: "{item["id"]}", name: "{item["name"]}", unit: "{item["unit"]}", emoji: "{item["emoji"]}",\n'
            f'    current: {item["current"]}, previous: {item["previous"]}, yearAgo: {item["yearAgo"]},\n'
            f'    history: [{history_str}],\n'
            f'    snark: "{snark_escaped}"\n'
            f'  }},'
        )
    lines.append("];")
    new_block = "\n".join(lines)

    html = re.sub(
        r'const FALLBACK_ITEMS = \[[\s\S]+?\];',
        new_block,
        html
    )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Update whatdideggsdonow.com prices from FRED")
    parser.add_argument("--key",      required=True, help="Your FRED API key")
    parser.add_argument("--html",     default="index.html", help="Path to index.html (default: index.html)")
    parser.add_argument("--dry-run",  action="store_true", help="Print results without updating HTML")
    args = parser.parse_args()

    print("\n🥚  What Did Eggs Do Now — Weekly Price Updater")
    print("=" * 52)
    print(f"  FRED API key: {args.key[:8]}{'*' * (len(args.key)-8)}")
    print(f"  Target file:  {args.html}")
    print()

    items = []
    for s in SERIES:
        item = fetch_item(s, args.key)
        items.append(item)
        time.sleep(1)  # avoid FRED rate limit (429)

    week_str = format_week(datetime.now())
    print(f"\n  Week string: {week_str}")

    if args.dry_run:
        print("\n  DRY RUN — no files written. Results:")
        print(json.dumps(items, indent=2, ensure_ascii=False))
    else:
        update_html(args.html, items, week_str)
        print(f"\n✅  {args.html} updated for week of {week_str}")
        print("    Deploy index.html to publish the update.\n")


if __name__ == "__main__":
    main()
