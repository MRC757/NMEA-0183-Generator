"""
tests/test_nmea_parser.py
Unit tests for core/nmea_parser.py — no hardware, no UI required.
Run with:  python -m pytest tests/test_nmea_parser.py -v
"""

import pytest
from core.nmea_parser import (
    calculate_checksum,
    build_sentence,
    build_custom_sentence,
    parse_sentence,
    parse_gga,
    parse_rmc,
    parse_fields,
)


# ---------------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------------

class TestChecksum:

    def test_known_gga_checksum(self):
        # Standard known sentence: $GPGGA,...*47
        body = "GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,"
        assert calculate_checksum(body) == "47"

    def test_known_rmc_checksum(self):
        body = "GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W"
        assert calculate_checksum(body) == "6A"

    def test_empty_body(self):
        # XOR of nothing is 0
        assert calculate_checksum("") == "00"

    def test_single_char(self):
        assert calculate_checksum("A") == f"{ord('A'):02X}"

    def test_returns_uppercase(self):
        result = calculate_checksum("GPGGA")
        assert result == result.upper()

    def test_returns_two_chars(self):
        result = calculate_checksum("X")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Build sentence
# ---------------------------------------------------------------------------

class TestBuildSentence:

    def test_gga_structure(self):
        fields = [
            "123519", "4807.038", "N", "01131.000", "E",
            "1", "08", "0.9", "545.4", "M", "46.9", "M", "", ""
        ]
        result = build_sentence("GP", "GGA", fields)
        assert result.startswith("$GPGGA,")
        assert result.endswith("\r\n")
        assert "*" in result

    def test_checksum_is_valid(self):
        fields = ["123519", "4807.038", "N", "01131.000", "E",
                  "1", "08", "0.9", "545.4", "M", "46.9", "M", "", ""]
        result = build_sentence("GP", "GGA", fields).strip()
        body, cs = result[1:].rsplit("*", 1)
        assert calculate_checksum(body) == cs.upper()

    def test_empty_fields(self):
        result = build_sentence("GP", "RMC", [])
        assert result.startswith("$GPRMC,")
        assert result.endswith("\r\n")

    def test_rmc_known_checksum(self):
        fields = [
            "123519", "A", "4807.038", "N", "01131.000", "E",
            "022.4", "084.4", "230394", "003.1", "W"
        ]
        result = build_sentence("GP", "RMC", fields).strip()
        body, cs = result[1:].rsplit("*", 1)
        assert calculate_checksum(body) == cs.upper()

    def test_talker_and_sentence_concatenated(self):
        result = build_sentence("II", "HDT", ["45.0", "T"])
        assert result.startswith("$IIHDT,")


# ---------------------------------------------------------------------------
# Build custom sentence
# ---------------------------------------------------------------------------

class TestBuildCustomSentence:

    def test_adds_dollar_and_checksum(self):
        result = build_custom_sentence("PGRME,3.0,M,4.0,M,5.0,M")
        assert result.startswith("$")
        assert "*" in result
        assert result.endswith("\r\n")

    def test_strips_existing_dollar(self):
        result = build_custom_sentence("$PGRME,3.0,M")
        assert result.startswith("$PGRME")
        # Should not have $$
        assert not result.startswith("$$")

    def test_strips_existing_checksum(self):
        # If template already has a (possibly wrong) checksum, it strips it
        result = build_custom_sentence("PGRME,3.0,M*ZZ")
        body, cs = result.strip()[1:].rsplit("*", 1)
        assert calculate_checksum(body) == cs.upper()

    def test_checksum_valid(self):
        template = "PGRME,3.0,M,4.0,M,5.0,M"
        result = build_custom_sentence(template).strip()
        body, cs = result[1:].rsplit("*", 1)
        assert calculate_checksum(body) == cs.upper()


# ---------------------------------------------------------------------------
# Parse sentence
# ---------------------------------------------------------------------------

class TestParseSentence:

    def test_valid_gga(self):
        raw = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        result = parse_sentence(raw)
        assert result is not None
        assert result["talker_id"] == "GP"
        assert result["sentence_id"] == "GGA"
        assert result["checksum_valid"] is True
        assert result["fields"][0] == "123519"

    def test_valid_rmc(self):
        raw = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        result = parse_sentence(raw)
        assert result is not None
        assert result["sentence_id"] == "RMC"
        assert result["checksum_valid"] is True

    def test_invalid_checksum(self):
        raw = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*FF"
        result = parse_sentence(raw)
        assert result is not None
        assert result["checksum_valid"] is False

    def test_no_checksum(self):
        raw = "$GPGGA,123519,4807.038,N"
        result = parse_sentence(raw)
        assert result is not None
        assert result["checksum_valid"] is False

    def test_empty_string(self):
        assert parse_sentence("") is None

    def test_no_dollar(self):
        assert parse_sentence("GPGGA,123519") is None

    def test_whitespace_stripped(self):
        raw = "  $GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A  "
        result = parse_sentence(raw)
        assert result is not None

    def test_ais_exclamation_prefix(self):
        # AIS sentences use '!' instead of '$'
        raw = "!AIVDM,1,1,,A,13HOI:0P0000000000000000000,0*6F"
        result = parse_sentence(raw)
        assert result is not None

    def test_proprietary_sentence(self):
        raw = "$PGRME,3.0,M,4.0,M,5.0,M*20"
        result = parse_sentence(raw)
        assert result is not None
        assert result["sentence_id"] == "GRME"

    def test_fields_list(self):
        raw = "$GPGLL,4807.038,N,01131.000,E,123519,A,A*7F"
        result = parse_sentence(raw)
        assert result is not None
        assert len(result["fields"]) >= 6

    def test_roundtrip(self):
        """Build a sentence then parse it back — should be consistent."""
        fields = ["000000.00", "0000.00000", "N", "00000.00000", "E",
                  "1", "08", "1.0", "0.0", "M", "0.0", "M", "", ""]
        built = build_sentence("GP", "GGA", fields).strip()
        parsed = parse_sentence(built)
        assert parsed is not None
        assert parsed["checksum_valid"] is True
        assert parsed["sentence_id"] == "GGA"
        assert parsed["talker_id"] == "GP"


# ---------------------------------------------------------------------------
# Field parsers
# ---------------------------------------------------------------------------

class TestFieldParsers:

    def test_parse_gga_fields(self):
        fields = [
            "123519", "4807.038", "N", "01131.000", "E",
            "1", "08", "0.9", "545.4", "M", "46.9", "M", "", ""
        ]
        result = parse_gga(fields)
        assert result["utc_time"] == "123519"
        assert result["latitude"] == "4807.038"
        assert result["lat_dir"] == "N"
        assert result["fix_quality"] == "1"
        assert result["num_satellites"] == "08"
        assert result["altitude"] == "545.4"

    def test_parse_rmc_fields(self):
        fields = [
            "123519", "A", "4807.038", "N", "01131.000", "E",
            "022.4", "084.4", "230394", "003.1", "W", "A"
        ]
        result = parse_rmc(fields)
        assert result["status"] == "A"
        assert result["speed_knots"] == "022.4"
        assert result["date"] == "230394"
        assert result["mode"] == "A"

    def test_parse_gga_short_fields(self):
        """parse_gga should pad with empty strings if fields are missing."""
        result = parse_gga(["123519", "4807.038"])
        assert result["utc_time"] == "123519"
        assert result["longitude"] == ""  # Missing — should be empty string

    def test_parse_fields_dispatch_gga(self):
        fields = ["123519", "4807.038", "N", "01131.000", "E",
                  "1", "08", "0.9", "545.4", "M", "46.9", "M", "", ""]
        result = parse_fields("GGA", fields)
        assert result is not None
        assert "utc_time" in result

    def test_parse_fields_dispatch_rmc(self):
        fields = ["123519", "A", "4807.038", "N", "01131.000", "E",
                  "022.4", "084.4", "230394", "003.1", "W", "A"]
        result = parse_fields("RMC", fields)
        assert result is not None
        assert "status" in result

    def test_parse_fields_unknown_sentence(self):
        result = parse_fields("XYZ", ["a", "b"])
        assert result is None

    def test_parse_fields_case_insensitive(self):
        fields = ["123519", "4807.038", "N", "01131.000", "E",
                  "1", "08", "0.9", "545.4", "M", "46.9", "M", "", ""]
        result = parse_fields("gga", fields)
        assert result is not None
