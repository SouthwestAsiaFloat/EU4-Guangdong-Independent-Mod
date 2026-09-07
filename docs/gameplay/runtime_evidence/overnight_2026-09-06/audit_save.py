"""Read current country references from a disposable EU4 text/ZIP save."""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
from encode_eu4_chinese_localisation import from_escaped_bytes


def block(data, opening):
    depth = 0
    quoted = escaped = False
    for pos in range(opening, len(data)):
        c = data[pos]
        if quoted:
            if escaped:
                escaped = False
            elif c == 92:
                escaped = True
            elif c == 34:
                quoted = False
        elif c == 34:
            quoted = True
        elif c == 123:
            depth += 1
        elif c == 125:
            depth -= 1
            if depth == 0:
                return data[opening:pos + 1]
    raise ValueError("unclosed block")


def fields(data, key, tabs=2):
    pattern = rb"(?m)^" + b"\t" * tabs + key.encode() + rb"=(.*)"
    out = []
    for match in re.finditer(pattern, data):
        value = match.group(1)
        if value.startswith(b"{"):
            value = block(data, match.start(1))
        out.append(value)
    return out


def decoded(value):
    return from_escaped_bytes(value)


def audit(path, tags):
    raw = path.read_bytes()
    data = zipfile.ZipFile(path).read("gamestate") if zipfile.is_zipfile(path) else raw
    match = re.search(rb"(?m)^countries=\{", data)
    if not match:
        raise ValueError("missing top-level countries")
    countries = block(data, match.end() - 1)
    result = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
              "date": re.search(rb"(?m)^date=([^\n]+)", data).group(1).decode(),
              "countries": {}, "trade_leagues": []}
    for tag in tags:
        match = re.search(rb"(?m)^\t" + tag.encode() + rb"=\{", countries)
        if not match:
            result["countries"][tag] = {"missing_country_block": True}
            continue
        country = block(countries, match.end() - 1)
        entry = {}
        for key in ("government", "government_rank", "flags", "variables", "last_election",
                    "republican_tradition", "stability", "prestige", "capital", "powers",
                    "owned_provinces", "monarch", "heir", "top_faction", "parliament",
                    "statists_vs_monarchists", "raw_development", "development",
                    "num_of_cities", "realm_development"):
            values = fields(country, key)
            if values:
                entry[key] = decoded(values[-1])
        for key in ("estate", "faction"):
            entry[key] = [decoded(value) for value in fields(country, key)]
        for role in ("monarch", "heir"):
            refs = fields(country, role)
            entry[role + "_current_ref_present"] = bool(refs)
            if not refs:
                continue
            person_id = re.search(rb"\bid=(\d+)", refs[-1]).group(1)
            records = []
            # Resolve full historical/current records by the actual type-48 id.
            # The country-local history is sufficient for opening incumbents;
            # an unresolved external saved character is explicitly marked.
            for m in re.finditer(rb"(?m)^(\t+)(?:monarch|heir|queen)=\{", country):
                record = block(country, m.end() - 1)
                if b"name=" in record and re.search(rb"\bid=" + person_id + rb"\s+type=48\b", record):
                    records.append(decoded(record))
            entry[role + "_records"] = records
            entry[role + "_resolution"] = "country-local" if records else "external/unresolved"
        result["countries"][tag] = entry
    for match in re.finditer(rb"(?m)^trade_league=\{", data):
        result["trade_leagues"].append(decoded(block(data, match.end() - 1)))
    result["zhou_state"] = {}
    for match in re.finditer(rb"(?m)^\t([A-Z0-9]{3})=\{", countries):
        country = block(countries, match.end() - 1)
        flag_values = fields(country, "flags")
        flags = flag_values[-1] if flag_values else b""
        if not any(name in flags for name in
                   (b"zhx_member=", b"zhx_major_feudatory=", b"zhx_feudatory_used_this_term=")):
            continue
        variables = fields(country, "variables")
        variable_block = variables[-1] if variables else b""
        province_values = fields(country, "owned_provinces")
        entry = {"owned_count": len(re.findall(rb"\d+", province_values[-1])) if province_values else 0}
        for flag in ("zhx_member", "zhx_major_feudatory", "zhx_feudatory_used_this_term",
                     "zhx_feudatory_request_pending", "zhx_merit_active_contribution_this_term"):
            found = re.search(rb"(?m)^\t\t\t" + flag.encode() + rb"=([^\n]+)", flags)
            entry[flag] = found.group(1).decode() if found else None
        for key in ("zhx_merit", "zhx_merit_term", "zhx_merit_rank_cache",
                    "zhx_merit_term_year", "zhx_merit_term_years_remaining"):
            found = re.search(rb"(?m)^\t\t\t" + key.encode() + rb"=([^\n]+)", variable_block)
            entry[key] = found.group(1).decode() if found else None
        for key in ("government", "government_rank", "power_projection"):
            values = fields(country, key)
            entry[key] = decoded(values[-1]) if values else None
        result["zhou_state"][match.group(1).decode()] = entry
    result["saved_zhou_targets"] = []
    for match in re.finditer(rb"(?m)^saved_event_target=\{", data):
        value = block(data, match.end() - 1)
        if any(key in value for key in (b"zhx_", b"gdd_principal_vassal")):
            result["saved_zhou_targets"].append(decoded(value))
    return result


if __name__ == "__main__":
    path = Path(sys.argv[1]).resolve()
    tags = sys.argv[2:] or "GUI NUN TZZ LIL DAI GDD CZC HAK HYM CDE JJG HYA WHU ZHO CZH".split()
    print(json.dumps(audit(path, tags), ensure_ascii=False, indent=2))
