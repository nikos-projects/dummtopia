#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DUMMTOPIA - Headless Mode
All game actions are driven by --flags. No input(), no QTEs, no interactive prompts.
State is persisted to a JSON save file between commands.

USAGE OVERVIEW:
  python dummtopia_headless.py --status
  python dummtopia_headless.py --init --character Philipp --name MyDealer
  python dummtopia_headless.py --buy normal --qty 3
  python dummtopia_headless.py --set-price normal --price 18.0
  python dummtopia_headless.py --serve
  python dummtopia_headless.py --serve --ticks 5
  python dummtopia_headless.py --sell --customer Stefan
  python dummtopia_headless.py --sell --customer Stefan --special-price 12.0
  python dummtopia_headless.py --deliver-sample Stefanie
  python dummtopia_headless.py --upgrade
  python dummtopia_headless.py --rebirth
  python dummtopia_headless.py --rebirth-perk "Goldene Nase"
  python dummtopia_headless.py --contact-customer Stefanie
  python dummtopia_headless.py --buy-distraction "Dummy-Kiosk"
  python dummtopia_headless.py --mafia-borrow --amount 50
  python dummtopia_headless.py --mafia-repay
  python dummtopia_headless.py --mafia-repay-partial --amount 25
  python dummtopia_headless.py --inventory
  python dummtopia_headless.py --customers
  python dummtopia_headless.py --reset

All output is JSON on stdout. Exit code 0 = success, 1 = error.
"""

import argparse
import json
import math
import os
import random
import sys
import time

# ─────────────────────────────────────────────────
#  ITEM DEFINITIONS
# ─────────────────────────────────────────────────

SPRAY_DATA = {
    "normal":  {"name": "Normales Nasenspray",          "base_price": 15},
    "premium": {"name": "Premium Nasenspray",           "base_price": 35},
    "ultra":   {"name": "Ultra Nasenspray (Industrial)","base_price": 75},
    "menthol": {"name": "Menthol-Nasenspray",           "base_price": 22},
}

# ─────────────────────────────────────────────────
#  CHARACTER STATS
# ─────────────────────────────────────────────────

CHARACTER_STATS = {
    "Philipp": {
        "selling_power": 1.25,
        "charisma":      0.80,
        "picky_bonus":   0.15,
        "wtp_up_chance": 0.05,
        "win_bonus":     0.08,
    },
    "Joseph": {
        "selling_power": 0.85,
        "charisma":      1.30,
        "picky_bonus":  -0.05,
        "wtp_up_chance": 0.20,
        "win_bonus":     0.15,
    },
}

# ─────────────────────────────────────────────────
#  CUSTOMER DEFINITIONS
# ─────────────────────────────────────────────────

CUSTOMER_DATA = {
    "Stefan":    {"wtp": 5, "winnable": False, "gender": "m"},
    "Johnathan": {"wtp": 2, "winnable": False, "gender": "m"},
    "Bob":       {"wtp": 4, "winnable": False, "gender": "m"},
    "Klaus":     {"wtp": 6, "winnable": False, "gender": "m"},
    "Dieter":    {"wtp": 5, "winnable": False, "gender": "m"},
    "Hans":      {"wtp": 3, "winnable": False, "gender": "m"},
    "Marco":     {"wtp": 7, "winnable": False, "gender": "m"},
    "Tobias":    {"wtp": 5, "winnable": False, "gender": "m"},
    "Felix":     {"wtp": 6, "winnable": False, "gender": "m"},
    "Patrick":   {"wtp": 8, "winnable": False, "gender": "m"},
    "Lukas":     {"wtp": 4, "winnable": False, "gender": "m"},
    "Tim":       {"wtp": 3, "winnable": False, "gender": "m"},
    "Nico":      {"wtp": 2, "winnable": False, "gender": "m"},
    "Fatima":    {"wtp": 7, "winnable": False, "gender": "f"},
    "Sandra":    {"wtp": 6, "winnable": False, "gender": "f"},
    "Melanie":   {"wtp": 5, "winnable": False, "gender": "f"},
    "Jessica":   {"wtp": 4, "winnable": False, "gender": "f"},
    "Petra":     {"wtp": 8, "winnable": False, "gender": "f"},
    "Anna":      {"wtp": 3, "winnable": False, "gender": "f"},
    "Leonie":    {"wtp": 6, "winnable": False, "gender": "f"},
    "Sabine":    {"wtp": 7, "winnable": False, "gender": "f"},
    "Ralf":      {"wtp": 3, "winnable": False, "gender": "m"},
    "Gerhard":   {"wtp": 4, "winnable": False, "gender": "m"},
    # Winnable customers
    "Stefanie":  {"wtp": 9, "winnable": True, "win_chance": 0.90, "gender": "f"},
    "Dr_Müller": {"wtp": 9, "winnable": True, "win_chance": 0.65, "gender": "m"},
    "Horst":     {"wtp": 6, "winnable": True, "win_chance": 0.70, "gender": "m"},
    "Claudia":   {"wtp": 8, "winnable": True, "win_chance": 0.75, "gender": "f"},
    "Erwin":     {"wtp": 7, "winnable": True, "win_chance": 0.80, "gender": "m"},
    "Natascha":  {"wtp": 8, "winnable": True, "win_chance": 0.60, "gender": "f"},
    "Benjamin":  {"wtp": 3, "winnable": True, "win_chance": 0.55, "gender": "m"},
    "Ingrid":    {"wtp": 6, "winnable": True, "win_chance": 0.85, "gender": "f"},
    "Markus":    {"wtp": 5, "winnable": True, "win_chance": 0.50, "gender": "m"},
    "Yara":      {"wtp": 7, "winnable": True, "win_chance": 0.72, "gender": "f"},
    "Dietmar":   {"wtp": 9, "winnable": True, "win_chance": 0.78, "gender": "m"},
}

# ─────────────────────────────────────────────────
#  SAVE / LOAD
# ─────────────────────────────────────────────────

SAVE_FILE = os.path.expanduser("~/.dummtopia_headless_save.json")

DEFAULT_STATE = {
    "first_launch": True,
    "dealer_name": "Philipp",
    "character": "Philipp",
    "balance": 50.0,
    "rebirth_points": 0,
    "rebirth_count": 0,
    "level": 1,
    "xp": 0,
    "inventory": ["normal", "normal"],
    "hidden_stash": [],
    "custom_prices": {},
    "customer_ratings": {},
    "customer_wtp_overrides": {},   # per-customer WTP bumps, keyed by name
    "unlocked_customers": [
        "Stefan", "Johnathan", "Bob",
        "Klaus", "Dieter", "Hans", "Marco", "Tobias", "Felix", "Patrick",
        "Lukas", "Tim", "Nico", "Fatima", "Sandra", "Melanie", "Jessica",
        "Petra", "Anna", "Leonie", "Sabine", "Ralf", "Gerhard",
    ],
    "winnable_customers": [
        "Stefanie", "Dr_Müller", "Horst", "Claudia", "Erwin", "Natascha",
        "Benjamin", "Ingrid", "Markus", "Yara", "Dietmar",
    ],
    "won_customers": [],
    "pending_samples": [],
    "settings": {
        "police_interval_min": 60,
        "police_interval_max": 120,
        "day_length_seconds": 1200,
    },
    "total_sales": 0,
    "total_busted": 0,
    "loan_amount": 0.0,
    "loan_deadline": None,
    "ingame_start_real": None,
    "ingame_day_notified": 0,
    "wtp_bonus": 0,
    "police_skip": 0,
    # Headless serve state — tracks last police event so --serve advances time properly
    "next_police_at": None,
    "under_inspection": False,
    "inspection_end_at": None,
}

def load_state():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_STATE)
        merged.update(data)
        merged_settings = dict(DEFAULT_STATE["settings"])
        merged_settings.update(data.get("settings", {}))
        merged["settings"] = merged_settings
        return merged
    return dict(DEFAULT_STATE)

def save_state(state):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def out(obj):
    """Print JSON result and exit 0."""
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(0)

def err(msg, details=None):
    """Print JSON error and exit 1."""
    payload = {"ok": False, "error": msg}
    if details:
        payload["details"] = details
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(1)

# ─────────────────────────────────────────────────
#  GAME LOGIC HELPERS
# ─────────────────────────────────────────────────

INGAME_WEEK_DAYS  = 7
INGAME_WEEKDAYS   = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

def get_ingame_time(state):
    start = state.get("ingame_start_real")
    if not start:
        return 1, 8, 0
    day_len = state["settings"]["day_length_seconds"]
    elapsed = time.time() - start
    total_days = int(elapsed // day_len)
    day = (total_days % INGAME_WEEK_DAYS) + 1
    day_progress = (elapsed % day_len) / day_len
    ih = int(day_progress * 24)
    im = int((day_progress * 24 * 60) % 60)
    return day, ih, im

def get_loan_deadline_seconds(state):
    return 7 * state["settings"]["day_length_seconds"]

def sell_chance(base_price, set_price, wtp):
    ratio = set_price / base_price
    tolerance = 0.05 + (wtp / 10) * 0.5
    threshold = 1.0 + tolerance
    if ratio <= threshold:
        return 0.95
    penalty = (ratio - threshold) * 1.5
    return round(max(0.05, 0.95 - penalty), 2)

def sell_chance_character(base_price, set_price, wtp, character, gender):
    base = sell_chance(base_price, set_price, wtp)
    stats = CHARACTER_STATS.get(character, CHARACTER_STATS["Philipp"])
    if gender == "m":
        modifier = (stats["selling_power"] - 1.0) * 0.3
    else:
        modifier = (stats["charisma"] - 1.0) * 0.3
    if wtp < 4:
        modifier += stats["picky_bonus"]
    return round(min(0.97, max(0.04, base + modifier)), 2)

def effective_wtp(state, name):
    base = CUSTOMER_DATA[name]["wtp"]
    override = state.get("customer_wtp_overrides", {}).get(name, 0)
    bonus = state.get("wtp_bonus", 0)
    return min(10, base + override + bonus)

def check_mafia_death(state):
    """Return (dead:bool, state). If dead, wipes save and returns default state."""
    if state.get("loan_amount", 0) <= 0:
        return False, state
    deadline = state.get("loan_deadline")
    if deadline and time.time() > deadline:
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
        new_state = dict(DEFAULT_STATE)
        save_state(new_state)
        return True, new_state
    return False, state

def ensure_police_scheduled(state):
    """Make sure next_police_at is set. Called at start of serve operations."""
    if not state.get("next_police_at"):
        s = state["settings"]
        delay = random.randint(s["police_interval_min"], s["police_interval_max"])
        state["next_police_at"] = time.time() + delay

# ─────────────────────────────────────────────────
#  COMMAND HANDLERS
# ─────────────────────────────────────────────────

def cmd_init(args):
    """Initialize / new game (or re-init character/name)."""
    char = args.character or "Philipp"
    if char not in CHARACTER_STATS:
        err(f"Unknown character '{char}'. Choose: {list(CHARACTER_STATS.keys())}")
    name = args.name or char

    state = dict(DEFAULT_STATE)
    state["character"] = char
    state["dealer_name"] = name
    state["first_launch"] = False
    state["ingame_start_real"] = time.time()
    save_state(state)
    out({"ok": True, "action": "init", "character": char, "dealer_name": name,
         "balance": state["balance"], "message": "New game started."})


def cmd_status(state):
    dead, state = check_mafia_death(state)
    if dead:
        out({"ok": True, "game_over": True,
             "message": "Mafia deadline passed. Save wiped. Use --init to start over."})

    d, ih, im = get_ingame_time(state)
    weekday = INGAME_WEEKDAYS[(d - 1) % 7]

    counts = {}
    for k in state["inventory"]:
        counts[k] = counts.get(k, 0) + 1
    inv_detail = [
        {"type": k, "name": SPRAY_DATA[k]["name"], "qty": v,
         "base_price": SPRAY_DATA[k]["base_price"],
         "your_price": state["custom_prices"].get(k, SPRAY_DATA[k]["base_price"])}
        for k, v in counts.items()
    ]

    loan_info = None
    if state.get("loan_amount", 0) > 0:
        remaining = max(0, int(state["loan_deadline"] - time.time())) if state.get("loan_deadline") else 0
        loan_info = {"amount": state["loan_amount"], "seconds_remaining": remaining}

    out({
        "ok": True,
        "dealer_name": state["dealer_name"],
        "character": state["character"],
        "balance": round(state["balance"], 2),
        "level": state["level"],
        "rebirth_count": state["rebirth_count"],
        "rebirth_points": state["rebirth_points"],
        "ingame_day": d,
        "ingame_weekday": weekday,
        "ingame_time": f"{ih:02d}:{im:02d}",
        "total_sales": state["total_sales"],
        "total_busted": state["total_busted"],
        "inventory": inv_detail,
        "hidden_stash": state["hidden_stash"],
        "pending_samples": state["pending_samples"],
        "won_customers": state["won_customers"],
        "unlocked_customers": state["unlocked_customers"],
        "loan": loan_info,
        "police_skip_charges": state.get("police_skip", 0),
        "wtp_bonus": state.get("wtp_bonus", 0),
        "under_inspection": state.get("under_inspection", False),
        "inspection_ends_in": max(0, int((state.get("inspection_end_at") or 0) - time.time()))
                              if state.get("under_inspection") else None,
    })


def cmd_inventory(state):
    counts = {}
    for k in state["inventory"]:
        counts[k] = counts.get(k, 0) + 1
    result = []
    for k, v in counts.items():
        d = SPRAY_DATA[k]
        price = state["custom_prices"].get(k, d["base_price"])
        result.append({
            "type": k,
            "name": d["name"],
            "qty": v,
            "base_price": d["base_price"],
            "your_price": price,
        })
    out({"ok": True, "inventory": result, "hidden_stash": state["hidden_stash"]})


def cmd_customers(state):
    all_known = state["unlocked_customers"] + state["won_customers"]
    available = [
        {
            "name": n,
            "wtp": effective_wtp(state, n),
            "gender": CUSTOMER_DATA[n]["gender"],
            "won": n in state["won_customers"],
        }
        for n in all_known
    ]
    winnable = [
        {
            "name": n,
            "wtp": effective_wtp(state, n),
            "win_chance": CUSTOMER_DATA[n]["win_chance"],
            "status": "pending_sample" if n in state["pending_samples"] else
                      "won" if n in state["won_customers"] else "available",
        }
        for n in state["winnable_customers"]
    ]
    out({"ok": True, "regular_customers": available, "winnable_customers": winnable})


def cmd_buy(args, state):
    dead, state = check_mafia_death(state)
    if dead:
        err("Mafia killed you. Use --init to restart.")

    key = args.buy
    if key not in SPRAY_DATA:
        err(f"Unknown spray type '{key}'. Available: {list(SPRAY_DATA.keys())}")

    lvl = state["level"]
    # Unlock rules
    if key == "premium" and lvl < 2:
        err("Premium Nasenspray requires level 2.")
    if key == "ultra" and lvl < 3:
        err("Ultra Nasenspray requires level 3.")

    qty = max(1, args.qty or 1)
    d = SPRAY_DATA[key]
    cost = round(d["base_price"] * qty, 2)
    if cost > state["balance"]:
        err(f"Not enough money. Need €{cost}, have €{round(state['balance'],2)}.")

    state["balance"] = round(state["balance"] - cost, 2)
    state["inventory"].extend([key] * qty)
    save_state(state)
    out({"ok": True, "action": "buy", "type": key, "name": d["name"],
         "qty": qty, "cost": cost, "balance": state["balance"]})


def cmd_set_price(args, state):
    key = args.set_price
    if key not in SPRAY_DATA:
        err(f"Unknown spray type '{key}'.")
    price = args.price
    if price is None or price <= 0:
        err("Provide a positive --price value.")
    state["custom_prices"][key] = round(price, 2)
    save_state(state)

    d = SPRAY_DATA[key]
    chances = {str(wtp): round(sell_chance(d["base_price"], price, wtp) * 100) for wtp in [2, 5, 9]}
    out({"ok": True, "action": "set_price", "type": key, "price": round(price, 2),
         "sell_chances_by_wtp": chances})


def cmd_serve(args, state):
    """
    Simulate one tick of serve mode (customer visit or police check).
    --ticks N  run N ticks in a row (default 1).
    Each tick = one random event resolving (customer or police).
    Police QTE is replaced by automatic hide logic: all inventory moved to stash.
    Returns a list of events that happened.
    """
    dead, state = check_mafia_death(state)
    if dead:
        err("Mafia killed you. Use --init to restart.")

    if state.get("first_launch", True):
        err("Game not initialized. Use --init first.")

    ticks = max(1, args.ticks or 1)
    events = []
    ensure_police_scheduled(state)

    for _ in range(ticks):
        now = time.time()

        # Resolve end of ongoing inspection first
        if state.get("under_inspection"):
            if now >= (state.get("inspection_end_at") or 0):
                # Retrieve stash
                retrieved = list(state["hidden_stash"])
                state["inventory"].extend(state["hidden_stash"])
                state["hidden_stash"] = []
                state["under_inspection"] = False
                state["inspection_end_at"] = None
                events.append({"event": "inspection_ended", "stash_retrieved": retrieved})
            else:
                remaining = int((state["inspection_end_at"] or 0) - now)
                events.append({"event": "under_inspection", "seconds_remaining": remaining})
                continue

        # Police trigger?
        if now >= (state.get("next_police_at") or 0):
            inv = list(state["inventory"])
            if not inv:
                # Nothing to hide — quick inspection
                dur = random.randint(5, 15)
                state["under_inspection"] = True
                state["inspection_end_at"] = now + dur
                s = state["settings"]
                state["next_police_at"] = now + dur + random.randint(
                    s["police_interval_min"], s["police_interval_max"])
                events.append({"event": "police_check", "result": "nothing_found",
                               "inspection_duration": dur})
                continue

            if state.get("police_skip", 0) > 0:
                state["police_skip"] -= 1
                dur = random.randint(10, 20)
                state["under_inspection"] = True
                state["inspection_end_at"] = now + dur
                s = state["settings"]
                state["next_police_at"] = now + dur + random.randint(
                    s["police_interval_min"], s["police_interval_max"])
                events.append({"event": "police_check", "result": "corrupt_officer_used",
                               "inspection_duration": dur})
                continue

            # AUTO-HIDE: move everything to hidden stash (no QTE in headless mode)
            hidden = list(inv)
            state["hidden_stash"].extend(hidden)
            state["inventory"] = []
            dur = random.randint(30, 60)
            state["under_inspection"] = True
            state["inspection_end_at"] = now + dur
            s = state["settings"]
            state["next_police_at"] = now + dur + random.randint(
                s["police_interval_min"], s["police_interval_max"])
            events.append({"event": "police_check", "result": "auto_hidden",
                           "hidden_items": hidden, "inspection_duration": dur,
                           "note": "All inventory auto-hidden to stash. Retrieve with next --serve after inspection ends."})
            save_state(state)
            continue

        # Customer visit
        available_customers = list(state["unlocked_customers"]) + list(state["won_customers"])
        if not available_customers:
            events.append({"event": "no_customers_available"})
            continue

        name = random.choice(available_customers)
        cdata = CUSTOMER_DATA[name]
        wtp = effective_wtp(state, name)
        gender = cdata["gender"]
        inv = state["inventory"]

        if not inv:
            events.append({"event": "customer_visit", "customer": name,
                           "result": "no_inventory", "message": "No spray to sell."})
            continue

        spray_key = inv[0]
        d = SPRAY_DATA[spray_key]
        sell_price = state["custom_prices"].get(spray_key, d["base_price"])
        chance = sell_chance_character(d["base_price"], sell_price, wtp, state["character"], gender)

        if random.random() < chance:
            state["inventory"].remove(spray_key)
            state["balance"] = round(state["balance"] + sell_price, 2)
            state["total_sales"] += 1
            rating = round(
                random.uniform(3.5, 5.0) if sell_price <= d["base_price"] * 1.2
                else random.uniform(2.0, 3.5), 1)
            prev = state["customer_ratings"].get(name, rating)
            state["customer_ratings"][name] = round((prev + rating) / 2, 1)

            # WTP bump chance
            stats = CHARACTER_STATS.get(state["character"], CHARACTER_STATS["Philipp"])
            wtp_up_prob = stats["wtp_up_chance"]
            if gender == "f":
                wtp_up_prob *= stats["charisma"]
            wtp_bumped = False
            if random.random() < wtp_up_prob:
                overrides = state.setdefault("customer_wtp_overrides", {})
                overrides[name] = overrides.get(name, 0) + 1
                wtp_bumped = True

            events.append({"event": "customer_visit", "customer": name,
                           "result": "sold", "item": spray_key, "price": sell_price,
                           "balance": state["balance"], "sell_chance": chance,
                           "wtp_bumped": wtp_bumped})
        else:
            events.append({"event": "customer_visit", "customer": name,
                           "result": "rejected", "item": spray_key, "price": sell_price,
                           "sell_chance": chance})

    save_state(state)
    out({"ok": True, "ticks": ticks, "events": events,
         "balance": round(state["balance"], 2),
         "inventory_count": len(state["inventory"])})


def cmd_sell(args, state):
    """
    Direct sell attempt to a specific customer.
    --customer NAME  [required]
    --special-price FLOAT  [optional, for low-WTP customers]
    """
    dead, state = check_mafia_death(state)
    if dead:
        err("Mafia killed you. Use --init to restart.")

    name = args.customer
    if not name:
        err("Provide --customer NAME.")

    all_avail = state["unlocked_customers"] + state["won_customers"]
    if name not in all_avail:
        err(f"Customer '{name}' not available. Check --customers for list.")

    if state.get("under_inspection"):
        err("Currently under police inspection. Cannot sell.", {"inspection_ends_in":
            max(0, int((state.get("inspection_end_at") or 0) - time.time()))})

    inv = state["inventory"]
    if not inv:
        err("No inventory to sell.")

    cdata = CUSTOMER_DATA[name]
    wtp = effective_wtp(state, name)
    gender = cdata["gender"]

    # Handle pending sample delivery
    if name in state["pending_samples"]:
        state["pending_samples"].remove(name)
        stats = CHARACTER_STATS.get(state["character"], CHARACTER_STATS["Philipp"])
        win_chance = CUSTOMER_DATA[name].get("win_chance", 0.5)
        if gender == "f":
            win_chance = min(0.97, win_chance + stats["win_bonus"] * stats["charisma"])
        else:
            win_chance = min(0.97, win_chance + stats["win_bonus"])
        won = random.random() < win_chance
        if won:
            state["won_customers"].append(name)
        save_state(state)
        out({"ok": True, "action": "deliver_sample", "customer": name,
             "result": "won_customer" if won else "rejected",
             "win_chance": round(win_chance, 2)})

    spray_key = inv[0]
    d = SPRAY_DATA[spray_key]
    special = args.special_price
    sell_price = special if special else state["custom_prices"].get(spray_key, d["base_price"])

    chance = sell_chance_character(d["base_price"], sell_price, wtp, state["character"], gender)
    sold = random.random() < chance

    if sold:
        state["inventory"].remove(spray_key)
        state["balance"] = round(state["balance"] + sell_price, 2)
        state["total_sales"] += 1
        rating = round(
            random.uniform(3.5, 5.0) if sell_price <= d["base_price"] * 1.2
            else random.uniform(2.0, 3.5), 1)
        prev = state["customer_ratings"].get(name, rating)
        state["customer_ratings"][name] = round((prev + rating) / 2, 1)

        stats = CHARACTER_STATS.get(state["character"], CHARACTER_STATS["Philipp"])
        wtp_up_prob = stats["wtp_up_chance"]
        if gender == "f":
            wtp_up_prob *= stats["charisma"]
        wtp_bumped = False
        if special and random.random() < wtp_up_prob:
            overrides = state.setdefault("customer_wtp_overrides", {})
            overrides[name] = overrides.get(name, 0) + 1
            wtp_bumped = True

        save_state(state)
        out({"ok": True, "action": "sell", "customer": name, "item": spray_key,
             "price": sell_price, "result": "sold", "balance": state["balance"],
             "sell_chance": chance, "wtp_bumped": wtp_bumped})
    else:
        save_state(state)
        out({"ok": True, "action": "sell", "customer": name, "item": spray_key,
             "price": sell_price, "result": "rejected", "sell_chance": chance})


def cmd_deliver_sample(args, state):
    """Explicitly deliver a pending sample to a winnable customer."""
    name = args.deliver_sample
    if name not in state["pending_samples"]:
        err(f"No pending sample for '{name}'. Check --status.")

    state["pending_samples"].remove(name)
    cdata = CUSTOMER_DATA[name]
    gender = cdata["gender"]
    stats = CHARACTER_STATS.get(state["character"], CHARACTER_STATS["Philipp"])
    win_chance = cdata.get("win_chance", 0.5)
    if gender == "f":
        win_chance = min(0.97, win_chance + stats["win_bonus"] * stats["charisma"])
    else:
        win_chance = min(0.97, win_chance + stats["win_bonus"])

    won = random.random() < win_chance
    if won:
        state["won_customers"].append(name)
    save_state(state)
    out({"ok": True, "action": "deliver_sample", "customer": name,
         "result": "won_customer" if won else "rejected",
         "win_chance": round(win_chance, 2),
         "note": "Customer added to your regular pool." if won else "They weren't interested."})


def cmd_upgrade(state):
    """Attempt a level upgrade."""
    dead, state = check_mafia_death(state)
    if dead:
        err("Mafia killed you. Use --init to restart.")

    lvl = state["level"]
    max_level = 3

    if lvl >= max_level:
        err(f"Already at max level {max_level}. Use --rebirth to reset with bonus points.")

    ratings = list(state["customer_ratings"].values())
    avg_rating = (sum(ratings) / len(ratings)) if ratings else 3.0
    upgrade_cost = round(100 * (lvl ** 1.8) * (1 / max(avg_rating, 0.5)), 2)
    if state["rebirth_count"] > 0:
        upgrade_cost = round(upgrade_cost * 0.7, 2)

    if state["balance"] < upgrade_cost:
        err(f"Not enough money. Need €{upgrade_cost}, have €{round(state['balance'],2)}.",
            {"upgrade_cost": upgrade_cost, "balance": round(state["balance"], 2)})

    state["balance"] = round(state["balance"] - upgrade_cost, 2)
    state["level"] += 1
    save_state(state)
    unlocked = {2: ["premium spray", "customer shop", "phone system"],
                3: ["ultra spray", "distraction shop"]}.get(state["level"], [])
    out({"ok": True, "action": "upgrade", "new_level": state["level"],
         "cost": upgrade_cost, "balance": state["balance"], "unlocked": unlocked})


def cmd_rebirth(state):
    """Rebirth: reset to level 1 in exchange for rebirth points."""
    if state["level"] < 3:
        err("Must be at level 3 to rebirth.")
    state["rebirth_points"] += 3
    state["rebirth_count"] += 1
    state["level"] = 1
    state["balance"] = 50.0
    state["inventory"] = ["normal", "normal"]
    state["custom_prices"] = {}
    save_state(state)
    out({"ok": True, "action": "rebirth", "rebirth_count": state["rebirth_count"],
         "rebirth_points": state["rebirth_points"],
         "note": "Level reset to 1. Use --rebirth-perk to spend RP."})


def cmd_rebirth_perk(args, state):
    """Spend rebirth points on a perk."""
    PERKS = {
        "Goldene Nase":        {"cost": 1, "desc": "All prices -10%"},
        "VIP-Liste":           {"cost": 2, "desc": "+2 WTP for all customers"},
        "Korrupter Polizist":  {"cost": 3, "desc": "Police ignores you once"},
        "Schwarzmarkt-Kontakt":{"cost": 5, "desc": "Instantly unlock Ultra Nasenspray"},
    }
    perk_name = args.rebirth_perk
    if perk_name not in PERKS:
        err(f"Unknown perk '{perk_name}'. Available: {list(PERKS.keys())}")

    perk = PERKS[perk_name]
    if state["rebirth_points"] < perk["cost"]:
        err(f"Not enough RP. Need {perk['cost']}, have {state['rebirth_points']}.")

    state["rebirth_points"] -= perk["cost"]
    if "Goldene" in perk_name:
        for k in SPRAY_DATA:
            base = SPRAY_DATA[k]["base_price"]
            current = state["custom_prices"].get(k, base)
            state["custom_prices"][k] = round(current * 0.9, 2)
    elif "VIP" in perk_name:
        state["wtp_bonus"] = state.get("wtp_bonus", 0) + 2
    elif "Korrupt" in perk_name:
        state["police_skip"] = state.get("police_skip", 0) + 1
    elif "Schwarzmarkt" in perk_name:
        state["level"] = max(state["level"], 3)

    save_state(state)
    out({"ok": True, "action": "rebirth_perk", "perk": perk_name,
         "rebirth_points_remaining": state["rebirth_points"]})


def cmd_contact_customer(args, state):
    """Send a sample to a winnable customer (costs money)."""
    if state["level"] < 2:
        err("Requires level 2.")

    name = args.contact_customer
    winnable = state["winnable_customers"]
    already_won = state["won_customers"]
    pending = state["pending_samples"]

    if name not in winnable:
        err(f"'{name}' is not a winnable customer.")
    if name in already_won:
        err(f"'{name}' is already a won customer.")
    if name in pending:
        err(f"Sample already pending for '{name}'.")

    cost = 20 + CUSTOMER_DATA[name]["wtp"] * 5
    if state["balance"] < cost:
        err(f"Not enough money. Need €{cost}.", {"balance": round(state["balance"], 2)})

    state["balance"] = round(state["balance"] - cost, 2)
    state["pending_samples"].append(name)
    save_state(state)
    out({"ok": True, "action": "contact_customer", "customer": name, "cost": cost,
         "balance": state["balance"],
         "note": f"Sample sent. Use --deliver-sample {name} or --sell --customer {name} when they visit."})


def cmd_buy_distraction(args, state):
    """Buy a distraction to increase police intervals."""
    if state["level"] < 3:
        err("Requires level 3.")

    DISTRACTIONS = {
        "Dummy-Kiosk":     {"cost": 150, "bonus": 30,  "key": "min"},
        "Fake-Marktstand": {"cost": 300, "bonus": 60,  "key": "max"},
        "Bestechung":      {"cost": 500, "bonus": 120, "key": "both"},
    }
    name = args.buy_distraction
    if name not in DISTRACTIONS:
        err(f"Unknown distraction '{name}'. Available: {list(DISTRACTIONS.keys())}")

    d = DISTRACTIONS[name]
    if state["balance"] < d["cost"]:
        err(f"Not enough money. Need €{d['cost']}.", {"balance": round(state["balance"], 2)})

    state["balance"] = round(state["balance"] - d["cost"], 2)
    if d["key"] == "both":
        state["settings"]["police_interval_min"] += d["bonus"]
        state["settings"]["police_interval_max"] += d["bonus"]
    elif d["key"] == "min":
        state["settings"]["police_interval_min"] += d["bonus"]
    else:
        state["settings"]["police_interval_max"] += d["bonus"]

    save_state(state)
    out({"ok": True, "action": "buy_distraction", "item": name, "cost": d["cost"],
         "balance": state["balance"],
         "police_interval": {
             "min": state["settings"]["police_interval_min"],
             "max": state["settings"]["police_interval_max"],
         }})


def cmd_mafia_borrow(args, state):
    MAX_LOAN = 100.0
    if state.get("loan_amount", 0) > 0:
        err(f"Already have an active loan of €{state['loan_amount']}. Repay first.")
    amount = args.amount
    if not amount or amount <= 0:
        err("Provide a positive --amount.")
    amount = round(min(amount, MAX_LOAN), 2)
    deadline_secs = get_loan_deadline_seconds(state)
    state["loan_amount"] = amount
    state["loan_deadline"] = time.time() + deadline_secs
    state["balance"] = round(state["balance"] + amount, 2)
    save_state(state)
    out({"ok": True, "action": "mafia_borrow", "amount": amount,
         "balance": state["balance"],
         "deadline_seconds": int(deadline_secs),
         "warning": f"Repay €{amount} within {round(deadline_secs/3600,1)} real-hours or game over."})


def cmd_mafia_repay(state):
    amount = round(state.get("loan_amount", 0), 2)
    if amount <= 0:
        err("No active loan.")
    if state["balance"] < amount:
        err(f"Not enough money. Need €{amount}, have €{round(state['balance'],2)}.")
    state["balance"] = round(state["balance"] - amount, 2)
    state["loan_amount"] = 0.0
    state["loan_deadline"] = None
    save_state(state)
    out({"ok": True, "action": "mafia_repay", "paid": amount, "balance": state["balance"]})


def cmd_mafia_repay_partial(args, state):
    total_debt = round(state.get("loan_amount", 0), 2)
    if total_debt <= 0:
        err("No active loan.")
    pay = args.amount
    if not pay or pay <= 0:
        err("Provide a positive --amount.")
    pay = round(min(pay, total_debt), 2)
    if state["balance"] < pay:
        err(f"Not enough money. Need €{pay}, have €{round(state['balance'],2)}.")
    state["balance"] = round(state["balance"] - pay, 2)
    new_debt = round(total_debt - pay, 2)
    state["loan_amount"] = new_debt
    if new_debt <= 0:
        state["loan_deadline"] = None
    save_state(state)
    out({"ok": True, "action": "mafia_repay_partial", "paid": pay,
         "remaining_debt": new_debt, "balance": state["balance"]})


def cmd_reset():
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
    out({"ok": True, "action": "reset", "message": "Save file deleted. Use --init to start fresh."})


# ─────────────────────────────────────────────────
#  ARG PARSING & DISPATCH
# ─────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(
        description="DUMMTOPIA Headless — AI-agent-friendly game CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Init / meta
    p.add_argument("--init",           action="store_true", help="Start new game")
    p.add_argument("--character",      default="Philipp",   help="Character: Philipp | Joseph")
    p.add_argument("--name",           default=None,        help="Dealer name")
    p.add_argument("--status",         action="store_true", help="Show full game status")
    p.add_argument("--inventory",      action="store_true", help="Show inventory")
    p.add_argument("--customers",      action="store_true", help="List customers and WTP")
    p.add_argument("--reset",          action="store_true", help="Delete save file")

    # Economy
    p.add_argument("--buy",            metavar="TYPE",      help="Buy spray: normal|menthol|premium|ultra")
    p.add_argument("--qty",            type=int,            help="Quantity for --buy")
    p.add_argument("--set-price",      metavar="TYPE",      help="Set custom sell price for spray type")
    p.add_argument("--price",          type=float,          help="Price value for --set-price or --mafia-repay-partial")

    # Serve / sell
    p.add_argument("--serve",          action="store_true", help="Simulate serve tick(s)")
    p.add_argument("--ticks",          type=int, default=1, help="Number of ticks for --serve")
    p.add_argument("--sell",           action="store_true", help="Sell to a specific customer")
    p.add_argument("--customer",       metavar="NAME",      help="Customer name for --sell")
    p.add_argument("--special-price",  type=float,          dest="special_price",
                                       help="Override sell price for this transaction")
    p.add_argument("--deliver-sample", metavar="NAME",      dest="deliver_sample",
                                       help="Deliver pending sample to a customer")

    # Progression
    p.add_argument("--upgrade",        action="store_true", help="Upgrade to next level")
    p.add_argument("--rebirth",        action="store_true", help="Rebirth (level 3 only)")
    p.add_argument("--rebirth-perk",   metavar="PERK",      dest="rebirth_perk",
                                       help="Buy rebirth perk by name")
    p.add_argument("--contact-customer", metavar="NAME",    dest="contact_customer",
                                       help="Send sample to a winnable customer")
    p.add_argument("--buy-distraction", metavar="NAME",     dest="buy_distraction",
                                       help="Buy a police distraction item")

    # Mafia
    p.add_argument("--mafia-borrow",   action="store_true", help="Borrow from mafia")
    p.add_argument("--mafia-repay",    action="store_true", help="Repay full mafia loan")
    p.add_argument("--mafia-repay-partial", action="store_true",
                   dest="mafia_repay_partial",              help="Repay partial mafia loan (use --amount)")
    p.add_argument("--amount",         type=float,          help="Amount for borrow/repay")

    return p


def main():
    p = build_parser()
    args = p.parse_args()

    # Commands that don't need a loaded state
    if args.init:
        cmd_init(args)

    if args.reset:
        cmd_reset()

    # All other commands need state
    state = load_state()

    if state.get("first_launch", True) and not args.status:
        err("Game not initialized. Run --init first.")

    if args.status:
        cmd_status(state)
    elif args.inventory:
        cmd_inventory(state)
    elif args.customers:
        cmd_customers(state)
    elif args.buy:
        cmd_buy(args, state)
    elif args.set_price:
        cmd_set_price(args, state)
    elif args.serve:
        cmd_serve(args, state)
    elif args.sell:
        cmd_sell(args, state)
    elif args.deliver_sample:
        cmd_deliver_sample(args, state)
    elif args.upgrade:
        cmd_upgrade(state)
    elif args.rebirth:
        cmd_rebirth(state)
    elif args.rebirth_perk:
        cmd_rebirth_perk(args, state)
    elif args.contact_customer:
        cmd_contact_customer(args, state)
    elif args.buy_distraction:
        cmd_buy_distraction(args, state)
    elif args.mafia_borrow:
        cmd_mafia_borrow(args, state)
    elif args.mafia_repay:
        cmd_mafia_repay(state)
    elif args.mafia_repay_partial:
        cmd_mafia_repay_partial(args, state)
    else:
        p.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
