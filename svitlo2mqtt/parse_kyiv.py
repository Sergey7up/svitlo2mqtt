# -*- coding: utf-8 -*-
import json
import re
from typing import Dict, List, Optional, Tuple, Union, Mapping

# ====== Kyiv Digital JSON message parser (address-based outages) ======

def parse_kyiv_digital(text: str) -> Optional[Tuple[str, str, Dict]]:
    """
    Parse Kyiv Digital messages that contain a JSON object.

    Requirements: the JSON must contain at least 'group' and 'power'.
    The function is tolerant to wrapping: it extracts the substring from the
    first '{' to the last '}' and parses that.

    Returns a tuple: (typ, group_code, payload) where typ is {"ON","OFF"} and
    payload is the full JSON dict from the message (all fields), without adding
    timestamp (caller adds Telegram message timestamp).

    Приклади:
      OFF: {"power": false, "emergency": false, "time_to": 25, "group": "1.1", ...}
      ON:  {"power": true,  "group": "6.1", ...}
    """
    # Extract JSON block between the first '{' and the last '}'
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    body = text[start:end + 1]

    try:
        data = json.loads(body)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    if 'group' not in data or 'power' not in data:
        return None

    grp = str(data.get('group'))
    power_val = data.get('power')
    typ = 'ON' if bool(power_val) else 'OFF'

    # Pass-through payload, but drop keys that should not be published
    payload: Dict = {k: v for k, v in data.items() if k not in {"group", "text", "address"}}

    return (typ, grp, payload)


# ====== Groups summary parser ======

def parse_groups_summary(text: str) -> Optional[Tuple[Optional[int], Dict[str, int]]]:
    """
    Parse group summary text into total percentage and a dict of group->percentage.

    Input looks like:
        🟠 59% 🔴 🟠 🟠 🟠 🟠 🟠

        Група 1: 31% 11:37 📈
        Група 2: 51% 12:06
        Група 3: 60% 11:42 📈
        Група 4: 71% 12:06 📉
        Група 5: 74% 12:05 📉
        Група 6: 64% 11:34 📈

    Returns (total_or_None, {group_number: percentage, ...}).
    """
    # total from the header (first percentage occurrence)
    header = re.search(r"(\d{1,3})\s*%", text)
    total = int(header.group(1)) if header else None

    groups: Dict[str, int] = {}
    for m in re.finditer(r"(?mi)групп?а\s*([0-9]+(?:\.[0-9]+)?)\s*:\s*(\d{1,3})\s*%", text):
        gi = m.group(1)  # string, may include dot like '1.1'
        pv = int(m.group(2))
        groups[gi] = pv

    if not groups:
        return None
    return (total, groups)
