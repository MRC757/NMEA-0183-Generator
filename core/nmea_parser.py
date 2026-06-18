"""
core/nmea_parser.py
Low-level NMEA 0183 sentence encoding and decoding.
No external dependencies — pure Python string operations.
"""

from typing import Optional, Tuple, List


def calculate_checksum(sentence_body: str) -> str:
    """
    Calculate NMEA XOR checksum.
    Input: everything between '$' and '*' (exclusive).
    Returns: two-character uppercase hex string.
    """
    checksum = 0
    for char in sentence_body:
        checksum ^= ord(char)
    return f"{checksum:02X}"


def build_sentence(talker_id: str, sentence_id: str, fields: List[str]) -> str:
    """
    Build a complete NMEA sentence string with checksum.

    Example:
        build_sentence("GP", "GGA", ["123519", "4807.038", "N", ...])
        -> "$GPGGA,123519,4807.038,N,...*HH\r\n"
    """
    tag = f"{talker_id}{sentence_id}"
    body = tag + "," + ",".join(fields)
    checksum = calculate_checksum(body)
    return f"${body}*{checksum}\r\n"


def build_custom_sentence(template: str) -> str:
    """
    Build a sentence from a raw template string.
    Template should be the body only (no $, *, checksum, or CRLF).
    Example template: "PGRME,3.0,M,4.0,M,5.0,M"
    """
    body = template.strip().lstrip("$")
    if "*" in body:
        body = body.split("*")[0]
    checksum = calculate_checksum(body)
    return f"${body}*{checksum}\r\n"


def parse_sentence(raw: str) -> Optional[dict]:
    """
    Parse a raw NMEA sentence string into a dict.

    Returns:
        {
            "talker_id": str,
            "sentence_id": str,
            "fields": List[str],
            "checksum_valid": bool,
            "raw": str,
        }
        or None if the string is not a valid NMEA sentence.
    """
    raw = raw.strip()

    # Must start with $ or !
    if not raw or raw[0] not in ("$", "!"):
        return None

    # Split on '*' to separate body and checksum
    if "*" in raw:
        body_part, checksum_part = raw[1:].rsplit("*", 1)
        provided_checksum = checksum_part[:2].upper()
        calculated = calculate_checksum(body_part)
        checksum_valid = (provided_checksum == calculated)
    else:
        body_part = raw[1:]
        checksum_valid = False  # No checksum provided

    # Split body into fields
    parts = body_part.split(",")
    if not parts:
        return None

    tag = parts[0]
    fields = parts[1:]

    # Extract talker ID and sentence ID from tag
    if len(tag) >= 5:
        talker_id = tag[:2]
        sentence_id = tag[2:]
    elif len(tag) >= 3:
        talker_id = ""
        sentence_id = tag
    else:
        talker_id = ""
        sentence_id = tag

    return {
        "talker_id": talker_id,
        "sentence_id": sentence_id,
        "fields": fields,
        "checksum_valid": checksum_valid,
        "raw": raw,
    }


def parse_gga(fields: List[str]) -> dict:
    """Parse GGA fields into a named dict."""
    keys = [
        "utc_time", "latitude", "lat_dir", "longitude", "lon_dir",
        "fix_quality", "num_satellites", "hdop", "altitude", "alt_unit",
        "geoid_sep", "geoid_unit", "dgps_age", "dgps_id"
    ]
    return _zip_fields(keys, fields)


def parse_rmc(fields: List[str]) -> dict:
    """Parse RMC fields into a named dict."""
    keys = [
        "utc_time", "status", "latitude", "lat_dir", "longitude", "lon_dir",
        "speed_knots", "track_angle", "date", "mag_var", "mag_var_dir", "mode"
    ]
    return _zip_fields(keys, fields)


def parse_gll(fields: List[str]) -> dict:
    keys = [
        "latitude", "lat_dir", "longitude", "lon_dir",
        "utc_time", "status", "mode"
    ]
    return _zip_fields(keys, fields)


def parse_vtg(fields: List[str]) -> dict:
    keys = [
        "track_true", "true_ind", "track_mag", "mag_ind",
        "speed_knots", "knots_ind", "speed_kmh", "kmh_ind", "mode"
    ]
    return _zip_fields(keys, fields)


def parse_gsa(fields: List[str]) -> dict:
    keys = (
        ["mode1", "mode2"] +
        [f"sv{i:02d}" for i in range(1, 13)] +
        ["pdop", "hdop", "vdop"]
    )
    return _zip_fields(keys, fields)


def parse_gsv(fields: List[str]) -> dict:
    keys = ["num_msgs", "msg_num", "num_svs"] + [
        f"sv{i}_{k}"
        for i in range(1, 5)
        for k in ["prn", "elev", "az", "snr"]
    ]
    return _zip_fields(keys, fields)


def parse_zda(fields: List[str]) -> dict:
    keys = ["utc_time", "day", "month", "year", "local_tz_hr", "local_tz_min"]
    return _zip_fields(keys, fields)


# Map sentence_id -> parser function
PARSERS = {
    "GGA": parse_gga,
    "RMC": parse_rmc,
    "GLL": parse_gll,
    "VTG": parse_vtg,
    "GSA": parse_gsa,
    "GSV": parse_gsv,
    "ZDA": parse_zda,
}


def parse_fields(sentence_id: str, fields: List[str]) -> Optional[dict]:
    """
    Parse fields for a known sentence type.
    Returns named dict or None if no parser is available.
    """
    parser = PARSERS.get(sentence_id.upper())
    if parser:
        return parser(fields)
    return None


def _zip_fields(keys: List[str], values: List[str]) -> dict:
    """Zip keys and values, padding with empty strings if values are short."""
    result = {}
    for i, key in enumerate(keys):
        result[key] = values[i] if i < len(values) else ""
    return result
