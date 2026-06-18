"""
core/nmea_sentences.py
Defines all standard NMEA 0183 sentences and their fields.
Also supports user-defined custom/proprietary sentences.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class NmeaFieldDef:
    """Definition of a single field within an NMEA sentence."""
    name: str
    description: str
    units: str = ""
    default: str = ""
    choices: List[str] = field(default_factory=list)  # If limited set of valid values


@dataclass
class NmeaSentenceDef:
    """Definition of a standard NMEA sentence type."""
    sentence_id: str          # e.g. "GGA"
    description: str
    fields: List[NmeaFieldDef] = field(default_factory=list)
    category: str = "General"


# ---------------------------------------------------------------------------
# Full standard NMEA 0183 sentence definitions
# Fields are ordered as they appear in the sentence after the talker+type tag
# ---------------------------------------------------------------------------

STANDARD_SENTENCES: List[NmeaSentenceDef] = [

    # --- Navigation & Position ---
    NmeaSentenceDef("GGA", "Global Positioning System Fix Data", category="GPS", fields=[
        NmeaFieldDef("utc_time", "UTC Time (hhmmss.ss)", default="000000.00"),
        NmeaFieldDef("latitude", "Latitude (ddmm.mmmmm)", default="0000.00000"),
        NmeaFieldDef("lat_dir", "Latitude Direction", choices=["N", "S"], default="N"),
        NmeaFieldDef("longitude", "Longitude (dddmm.mmmmm)", default="00000.00000"),
        NmeaFieldDef("lon_dir", "Longitude Direction", choices=["E", "W"], default="E"),
        NmeaFieldDef("fix_quality", "Fix Quality", choices=["0","1","2","3","4","5","6"], default="1"),
        NmeaFieldDef("num_satellites", "Number of Satellites", default="08"),
        NmeaFieldDef("hdop", "Horizontal Dilution of Precision", default="1.0"),
        NmeaFieldDef("altitude", "Altitude", units="M", default="0.0"),
        NmeaFieldDef("alt_unit", "Altitude Unit", choices=["M"], default="M"),
        NmeaFieldDef("geoid_sep", "Geoid Separation", units="M", default="0.0"),
        NmeaFieldDef("geoid_unit", "Geoid Unit", choices=["M"], default="M"),
        NmeaFieldDef("dgps_age", "Age of DGPS Data", default=""),
        NmeaFieldDef("dgps_id", "DGPS Station ID", default=""),
    ]),

    NmeaSentenceDef("RMC", "Recommended Minimum Navigation Information", category="GPS", fields=[
        NmeaFieldDef("utc_time", "UTC Time (hhmmss.ss)", default="000000.00"),
        NmeaFieldDef("status", "Status", choices=["A", "V"], default="A"),
        NmeaFieldDef("latitude", "Latitude (ddmm.mmmmm)", default="0000.00000"),
        NmeaFieldDef("lat_dir", "Latitude Direction", choices=["N", "S"], default="N"),
        NmeaFieldDef("longitude", "Longitude (dddmm.mmmmm)", default="00000.00000"),
        NmeaFieldDef("lon_dir", "Longitude Direction", choices=["E", "W"], default="E"),
        NmeaFieldDef("speed_knots", "Speed Over Ground", units="knots", default="0.0"),
        NmeaFieldDef("track_angle", "Track Angle True", units="deg", default="0.0"),
        NmeaFieldDef("date", "Date (ddmmyy)", default="010124"),
        NmeaFieldDef("mag_var", "Magnetic Variation", units="deg", default=""),
        NmeaFieldDef("mag_var_dir", "Magnetic Variation Direction", choices=["E","W"], default=""),
        NmeaFieldDef("mode", "Mode Indicator", choices=["A","D","E","M","S","N"], default="A"),
    ]),

    NmeaSentenceDef("GLL", "Geographic Position - Latitude/Longitude", category="GPS", fields=[
        NmeaFieldDef("latitude", "Latitude (ddmm.mmmmm)", default="0000.00000"),
        NmeaFieldDef("lat_dir", "Latitude Direction", choices=["N","S"], default="N"),
        NmeaFieldDef("longitude", "Longitude (dddmm.mmmmm)", default="00000.00000"),
        NmeaFieldDef("lon_dir", "Longitude Direction", choices=["E","W"], default="E"),
        NmeaFieldDef("utc_time", "UTC Time (hhmmss.ss)", default="000000.00"),
        NmeaFieldDef("status", "Status", choices=["A","V"], default="A"),
        NmeaFieldDef("mode", "Mode Indicator", choices=["A","D","E","M","S","N"], default="A"),
    ]),

    NmeaSentenceDef("GNS", "Fix Data (multi-constellation)", category="GPS", fields=[
        NmeaFieldDef("utc_time", "UTC Time", default="000000.00"),
        NmeaFieldDef("latitude", "Latitude", default="0000.00000"),
        NmeaFieldDef("lat_dir", "Latitude Direction", choices=["N","S"], default="N"),
        NmeaFieldDef("longitude", "Longitude", default="00000.00000"),
        NmeaFieldDef("lon_dir", "Longitude Direction", choices=["E","W"], default="E"),
        NmeaFieldDef("mode", "Mode Indicator", default="AA"),
        NmeaFieldDef("num_satellites", "Number of Satellites", default="08"),
        NmeaFieldDef("hdop", "HDOP", default="1.0"),
        NmeaFieldDef("altitude", "Altitude", units="M", default="0.0"),
        NmeaFieldDef("geoid_sep", "Geoid Separation", units="M", default="0.0"),
        NmeaFieldDef("dgps_age", "Age of DGPS Data", default=""),
        NmeaFieldDef("dgps_id", "DGPS Station ID", default=""),
    ]),

    NmeaSentenceDef("DTM", "Datum Reference", category="GPS", fields=[
        NmeaFieldDef("datum", "Local Datum Code", default="W84"),
        NmeaFieldDef("subcode", "Local Datum Subcode", default=""),
        NmeaFieldDef("lat_offset", "Latitude Offset", units="min", default="0.0"),
        NmeaFieldDef("lat_dir", "Latitude Offset Direction", choices=["N","S"], default="N"),
        NmeaFieldDef("lon_offset", "Longitude Offset", units="min", default="0.0"),
        NmeaFieldDef("lon_dir", "Longitude Offset Direction", choices=["E","W"], default="E"),
        NmeaFieldDef("alt_offset", "Altitude Offset", units="M", default="0.0"),
        NmeaFieldDef("ref_datum", "Reference Datum", default="W84"),
    ]),

    # --- Satellites ---
    NmeaSentenceDef("GSA", "GPS DOP and Active Satellites", category="Satellites", fields=[
        NmeaFieldDef("mode1", "Selection Mode", choices=["A","M"], default="A"),
        NmeaFieldDef("mode2", "Fix Mode", choices=["1","2","3"], default="3"),
        NmeaFieldDef("sv01", "Satellite PRN 01", default=""),
        NmeaFieldDef("sv02", "Satellite PRN 02", default=""),
        NmeaFieldDef("sv03", "Satellite PRN 03", default=""),
        NmeaFieldDef("sv04", "Satellite PRN 04", default=""),
        NmeaFieldDef("sv05", "Satellite PRN 05", default=""),
        NmeaFieldDef("sv06", "Satellite PRN 06", default=""),
        NmeaFieldDef("sv07", "Satellite PRN 07", default=""),
        NmeaFieldDef("sv08", "Satellite PRN 08", default=""),
        NmeaFieldDef("sv09", "Satellite PRN 09", default=""),
        NmeaFieldDef("sv10", "Satellite PRN 10", default=""),
        NmeaFieldDef("sv11", "Satellite PRN 11", default=""),
        NmeaFieldDef("sv12", "Satellite PRN 12", default=""),
        NmeaFieldDef("pdop", "PDOP", default="1.0"),
        NmeaFieldDef("hdop", "HDOP", default="1.0"),
        NmeaFieldDef("vdop", "VDOP", default="1.0"),
    ]),

    NmeaSentenceDef("GSV", "Satellites in View", category="Satellites", fields=[
        NmeaFieldDef("num_msgs", "Number of Messages", default="1"),
        NmeaFieldDef("msg_num", "Message Number", default="1"),
        NmeaFieldDef("num_svs", "Satellites in View", default="0"),
        NmeaFieldDef("sv1_prn", "SV1 PRN", default=""),
        NmeaFieldDef("sv1_elev", "SV1 Elevation", units="deg", default=""),
        NmeaFieldDef("sv1_az", "SV1 Azimuth", units="deg", default=""),
        NmeaFieldDef("sv1_snr", "SV1 SNR", units="dB", default=""),
    ]),

    NmeaSentenceDef("GBS", "GPS Satellite Fault Detection", category="Satellites", fields=[
        NmeaFieldDef("utc_time", "UTC Time", default="000000.00"),
        NmeaFieldDef("lat_err", "Expected Latitude Error", units="M", default="0.0"),
        NmeaFieldDef("lon_err", "Expected Longitude Error", units="M", default="0.0"),
        NmeaFieldDef("alt_err", "Expected Altitude Error", units="M", default="0.0"),
        NmeaFieldDef("failed_sv", "Failed Satellite PRN", default=""),
        NmeaFieldDef("prob", "Probability of Missed Detection", default=""),
        NmeaFieldDef("bias", "Estimated Bias", units="M", default=""),
        NmeaFieldDef("bias_dev", "Standard Deviation of Bias", units="M", default=""),
    ]),

    # --- Speed & Track ---
    NmeaSentenceDef("VTG", "Track Made Good and Ground Speed", category="Speed & Track", fields=[
        NmeaFieldDef("track_true", "Track Degrees True", units="deg", default="0.0"),
        NmeaFieldDef("track_true_ind", "True Indicator", choices=["T"], default="T"),
        NmeaFieldDef("track_mag", "Track Degrees Magnetic", units="deg", default=""),
        NmeaFieldDef("track_mag_ind", "Magnetic Indicator", choices=["M"], default="M"),
        NmeaFieldDef("speed_knots", "Speed Over Ground", units="knots", default="0.0"),
        NmeaFieldDef("speed_knots_ind", "Knots Indicator", choices=["N"], default="N"),
        NmeaFieldDef("speed_kmh", "Speed Over Ground", units="km/h", default="0.0"),
        NmeaFieldDef("speed_kmh_ind", "KPH Indicator", choices=["K"], default="K"),
        NmeaFieldDef("mode", "Mode Indicator", choices=["A","D","E","M","S","N"], default="A"),
    ]),

    NmeaSentenceDef("VBW", "Dual Ground/Water Speed", category="Speed & Track", fields=[
        NmeaFieldDef("water_speed_long", "Longitudinal Water Speed", units="knots", default="0.0"),
        NmeaFieldDef("water_speed_trans", "Transverse Water Speed", units="knots", default="0.0"),
        NmeaFieldDef("water_status", "Water Speed Status", choices=["A","V"], default="A"),
        NmeaFieldDef("ground_speed_long", "Longitudinal Ground Speed", units="knots", default="0.0"),
        NmeaFieldDef("ground_speed_trans", "Transverse Ground Speed", units="knots", default="0.0"),
        NmeaFieldDef("ground_status", "Ground Speed Status", choices=["A","V"], default="A"),
    ]),

    NmeaSentenceDef("VHW", "Water Speed and Heading", category="Speed & Track", fields=[
        NmeaFieldDef("heading_true", "Heading True", units="deg", default="0.0"),
        NmeaFieldDef("heading_true_ind", "True Indicator", choices=["T"], default="T"),
        NmeaFieldDef("heading_mag", "Heading Magnetic", units="deg", default="0.0"),
        NmeaFieldDef("heading_mag_ind", "Magnetic Indicator", choices=["M"], default="M"),
        NmeaFieldDef("speed_knots", "Speed Through Water", units="knots", default="0.0"),
        NmeaFieldDef("speed_knots_ind", "Knots Indicator", choices=["N"], default="N"),
        NmeaFieldDef("speed_kmh", "Speed Through Water", units="km/h", default="0.0"),
        NmeaFieldDef("speed_kmh_ind", "KPH Indicator", choices=["K"], default="K"),
    ]),

    NmeaSentenceDef("VLW", "Distance Traveled Through Water", category="Speed & Track", fields=[
        NmeaFieldDef("total_water_dist", "Total Cumulative Water Distance", units="NM", default="0.0"),
        NmeaFieldDef("total_ind", "Total Distance Unit", choices=["N"], default="N"),
        NmeaFieldDef("water_dist", "Water Distance Since Reset", units="NM", default="0.0"),
        NmeaFieldDef("water_ind", "Distance Unit", choices=["N"], default="N"),
    ]),

    NmeaSentenceDef("VDR", "Set and Drift", category="Speed & Track", fields=[
        NmeaFieldDef("set_true", "Direction of Set True", units="deg", default="0.0"),
        NmeaFieldDef("set_true_ind", "True Indicator", choices=["T"], default="T"),
        NmeaFieldDef("set_mag", "Direction of Set Magnetic", units="deg", default="0.0"),
        NmeaFieldDef("set_mag_ind", "Magnetic Indicator", choices=["M"], default="M"),
        NmeaFieldDef("drift", "Drift Speed", units="knots", default="0.0"),
        NmeaFieldDef("drift_ind", "Knots Indicator", choices=["N"], default="N"),
    ]),

    # --- Heading ---
    NmeaSentenceDef("HDG", "Heading - Deviation & Variation", category="Heading", fields=[
        NmeaFieldDef("heading", "Magnetic Sensor Heading", units="deg", default="0.0"),
        NmeaFieldDef("deviation", "Magnetic Deviation", units="deg", default=""),
        NmeaFieldDef("dev_dir", "Deviation Direction", choices=["E","W"], default=""),
        NmeaFieldDef("variation", "Magnetic Variation", units="deg", default=""),
        NmeaFieldDef("var_dir", "Variation Direction", choices=["E","W"], default=""),
    ]),

    NmeaSentenceDef("HDM", "Heading - Magnetic", category="Heading", fields=[
        NmeaFieldDef("heading", "Heading Magnetic", units="deg", default="0.0"),
        NmeaFieldDef("indicator", "Magnetic Indicator", choices=["M"], default="M"),
    ]),

    NmeaSentenceDef("HDT", "Heading - True", category="Heading", fields=[
        NmeaFieldDef("heading", "Heading True", units="deg", default="0.0"),
        NmeaFieldDef("indicator", "True Indicator", choices=["T"], default="T"),
    ]),

    NmeaSentenceDef("ROT", "Rate of Turn", category="Heading", fields=[
        NmeaFieldDef("rate", "Rate of Turn", units="deg/min", default="0.0"),
        NmeaFieldDef("status", "Status", choices=["A","V"], default="A"),
    ]),

    NmeaSentenceDef("RSA", "Rudder Sensor Angle", category="Heading", fields=[
        NmeaFieldDef("starboard_angle", "Starboard Rudder Sensor Angle", units="deg", default="0.0"),
        NmeaFieldDef("starboard_status", "Starboard Status", choices=["A","V"], default="A"),
        NmeaFieldDef("port_angle", "Port Rudder Sensor Angle", units="deg", default=""),
        NmeaFieldDef("port_status", "Port Status", choices=["A","V"], default="V"),
    ]),

    # --- Depth ---
    NmeaSentenceDef("DBT", "Depth Below Transducer", category="Depth", fields=[
        NmeaFieldDef("depth_ft", "Depth in Feet", units="ft", default="0.0"),
        NmeaFieldDef("ft_ind", "Feet Indicator", choices=["f"], default="f"),
        NmeaFieldDef("depth_m", "Depth in Meters", units="M", default="0.0"),
        NmeaFieldDef("m_ind", "Meters Indicator", choices=["M"], default="M"),
        NmeaFieldDef("depth_fm", "Depth in Fathoms", units="F", default="0.0"),
        NmeaFieldDef("fm_ind", "Fathoms Indicator", choices=["F"], default="F"),
    ]),

    NmeaSentenceDef("DBS", "Depth Below Surface", category="Depth", fields=[
        NmeaFieldDef("depth_ft", "Depth in Feet", units="ft", default="0.0"),
        NmeaFieldDef("ft_ind", "Feet Indicator", choices=["f"], default="f"),
        NmeaFieldDef("depth_m", "Depth in Meters", units="M", default="0.0"),
        NmeaFieldDef("m_ind", "Meters Indicator", choices=["M"], default="M"),
        NmeaFieldDef("depth_fm", "Depth in Fathoms", units="F", default="0.0"),
        NmeaFieldDef("fm_ind", "Fathoms Indicator", choices=["F"], default="F"),
    ]),

    NmeaSentenceDef("DBK", "Depth Below Keel", category="Depth", fields=[
        NmeaFieldDef("depth_ft", "Depth in Feet", units="ft", default="0.0"),
        NmeaFieldDef("ft_ind", "Feet Indicator", choices=["f"], default="f"),
        NmeaFieldDef("depth_m", "Depth in Meters", units="M", default="0.0"),
        NmeaFieldDef("m_ind", "Meters Indicator", choices=["M"], default="M"),
        NmeaFieldDef("depth_fm", "Depth in Fathoms", units="F", default="0.0"),
        NmeaFieldDef("fm_ind", "Fathoms Indicator", choices=["F"], default="F"),
    ]),

    NmeaSentenceDef("DPT", "Depth of Water", category="Depth", fields=[
        NmeaFieldDef("depth", "Water Depth Relative to Transducer", units="M", default="0.0"),
        NmeaFieldDef("offset", "Offset from Transducer", units="M", default="0.0"),
        NmeaFieldDef("max_range", "Maximum Range Scale in Use", units="M", default=""),
    ]),

    # --- Wind & Weather ---
    NmeaSentenceDef("MWV", "Wind Speed and Angle", category="Wind & Weather", fields=[
        NmeaFieldDef("angle", "Wind Angle", units="deg", default="0.0"),
        NmeaFieldDef("reference", "Reference", choices=["R","T"], default="R"),
        NmeaFieldDef("speed", "Wind Speed", default="0.0"),
        NmeaFieldDef("speed_unit", "Wind Speed Units", choices=["K","M","N"], default="N"),
        NmeaFieldDef("status", "Status", choices=["A","V"], default="A"),
    ]),

    NmeaSentenceDef("MWD", "Wind Direction & Speed", category="Wind & Weather", fields=[
        NmeaFieldDef("direction_true", "Wind Direction True", units="deg", default="0.0"),
        NmeaFieldDef("true_ind", "True Indicator", choices=["T"], default="T"),
        NmeaFieldDef("direction_mag", "Wind Direction Magnetic", units="deg", default="0.0"),
        NmeaFieldDef("mag_ind", "Magnetic Indicator", choices=["M"], default="M"),
        NmeaFieldDef("speed_knots", "Wind Speed", units="knots", default="0.0"),
        NmeaFieldDef("knots_ind", "Knots Indicator", choices=["N"], default="N"),
        NmeaFieldDef("speed_ms", "Wind Speed", units="m/s", default="0.0"),
        NmeaFieldDef("ms_ind", "Meters/Second Indicator", choices=["M"], default="M"),
    ]),

    NmeaSentenceDef("MTW", "Mean Temperature of Water", category="Wind & Weather", fields=[
        NmeaFieldDef("temperature", "Water Temperature", units="C", default="20.0"),
        NmeaFieldDef("unit", "Temperature Unit", choices=["C"], default="C"),
    ]),

    NmeaSentenceDef("XDR", "Transducer Measurement", category="Wind & Weather", fields=[
        NmeaFieldDef("type1", "Transducer Type 1", default=""),
        NmeaFieldDef("data1", "Measurement Data 1", default=""),
        NmeaFieldDef("unit1", "Unit 1", default=""),
        NmeaFieldDef("name1", "Transducer Name 1", default=""),
    ]),

    # --- Waypoints & Routes ---
    NmeaSentenceDef("WPL", "Waypoint Location", category="Waypoints & Routes", fields=[
        NmeaFieldDef("latitude", "Latitude", default="0000.00000"),
        NmeaFieldDef("lat_dir", "Latitude Direction", choices=["N","S"], default="N"),
        NmeaFieldDef("longitude", "Longitude", default="00000.00000"),
        NmeaFieldDef("lon_dir", "Longitude Direction", choices=["E","W"], default="E"),
        NmeaFieldDef("waypoint_id", "Waypoint ID", default="WP001"),
    ]),

    NmeaSentenceDef("RTE", "Routes", category="Waypoints & Routes", fields=[
        NmeaFieldDef("num_msgs", "Total Number of Messages", default="1"),
        NmeaFieldDef("msg_num", "Message Number", default="1"),
        NmeaFieldDef("mode", "Message Mode", choices=["c","w"], default="c"),
        NmeaFieldDef("route_id", "Route Identifier", default="ROUTE1"),
        NmeaFieldDef("waypoint_ids", "Waypoint IDs (comma separated)", default=""),
    ]),

    NmeaSentenceDef("BOD", "Bearing - Waypoint to Waypoint", category="Waypoints & Routes", fields=[
        NmeaFieldDef("bearing_true", "Bearing True", units="deg", default="0.0"),
        NmeaFieldDef("true_ind", "True Indicator", choices=["T"], default="T"),
        NmeaFieldDef("bearing_mag", "Bearing Magnetic", units="deg", default="0.0"),
        NmeaFieldDef("mag_ind", "Magnetic Indicator", choices=["M"], default="M"),
        NmeaFieldDef("dest_id", "Destination Waypoint ID", default=""),
        NmeaFieldDef("orig_id", "Origin Waypoint ID", default=""),
    ]),

    NmeaSentenceDef("BWC", "Bearing & Distance to Waypoint - Great Circle", category="Waypoints & Routes", fields=[
        NmeaFieldDef("utc_time", "UTC Time", default="000000.00"),
        NmeaFieldDef("latitude", "Latitude", default="0000.00000"),
        NmeaFieldDef("lat_dir", "Latitude Direction", choices=["N","S"], default="N"),
        NmeaFieldDef("longitude", "Longitude", default="00000.00000"),
        NmeaFieldDef("lon_dir", "Longitude Direction", choices=["E","W"], default="E"),
        NmeaFieldDef("bearing_true", "Bearing True", units="deg", default="0.0"),
        NmeaFieldDef("true_ind", "True Indicator", choices=["T"], default="T"),
        NmeaFieldDef("bearing_mag", "Bearing Magnetic", units="deg", default="0.0"),
        NmeaFieldDef("mag_ind", "Magnetic Indicator", choices=["M"], default="M"),
        NmeaFieldDef("distance", "Distance to Waypoint", units="NM", default="0.0"),
        NmeaFieldDef("dist_ind", "Distance Unit", choices=["N"], default="N"),
        NmeaFieldDef("waypoint_id", "Waypoint ID", default=""),
        NmeaFieldDef("mode", "Mode Indicator", choices=["A","D","E","M","S","N"], default="A"),
    ]),

    NmeaSentenceDef("XTE", "Cross-Track Error, Measured", category="Waypoints & Routes", fields=[
        NmeaFieldDef("status1", "General Warning Status", choices=["A","V"], default="A"),
        NmeaFieldDef("status2", "Lock Warning Status", choices=["A","V"], default="A"),
        NmeaFieldDef("xte", "Cross Track Error", units="NM", default="0.0"),
        NmeaFieldDef("direction", "Direction to Steer", choices=["L","R"], default="L"),
        NmeaFieldDef("unit", "Distance Unit", choices=["N"], default="N"),
        NmeaFieldDef("mode", "Mode Indicator", choices=["A","D","E","M","S","N"], default="A"),
    ]),

    # --- Autopilot ---
    NmeaSentenceDef("APB", "Autopilot Sentence B", category="Autopilot", fields=[
        NmeaFieldDef("status1", "General Warning Status", choices=["A","V"], default="A"),
        NmeaFieldDef("status2", "Lock Warning Status", choices=["A","V"], default="A"),
        NmeaFieldDef("xte", "Cross Track Error", default="0.0"),
        NmeaFieldDef("xte_dir", "Direction to Steer", choices=["L","R"], default="L"),
        NmeaFieldDef("xte_unit", "XTE Unit", choices=["N"], default="N"),
        NmeaFieldDef("arrival", "Arrival Circle Entered", choices=["A","V"], default="V"),
        NmeaFieldDef("perpendicular", "Perpendicular Passed", choices=["A","V"], default="V"),
        NmeaFieldDef("bearing_origin", "Bearing Origin to Destination", units="deg", default="0.0"),
        NmeaFieldDef("bearing_type", "Bearing Type", choices=["M","T"], default="T"),
        NmeaFieldDef("dest_id", "Destination Waypoint ID", default=""),
        NmeaFieldDef("bearing_present", "Bearing Present to Destination", units="deg", default="0.0"),
        NmeaFieldDef("bearing_present_type", "Bearing Present Type", choices=["M","T"], default="T"),
        NmeaFieldDef("heading_to_steer", "Heading to Steer", units="deg", default="0.0"),
        NmeaFieldDef("heading_type", "Heading Type", choices=["M","T"], default="T"),
        NmeaFieldDef("mode", "Mode Indicator", choices=["A","D","E","M","S","N"], default="A"),
    ]),

    NmeaSentenceDef("APA", "Autopilot Sentence A", category="Autopilot", fields=[
        NmeaFieldDef("status1", "General Warning Status", choices=["A","V"], default="A"),
        NmeaFieldDef("status2", "Lock Warning Status", choices=["A","V"], default="A"),
        NmeaFieldDef("xte", "Cross Track Error", default="0.0"),
        NmeaFieldDef("xte_dir", "Direction to Steer", choices=["L","R"], default="L"),
        NmeaFieldDef("xte_unit", "XTE Unit", choices=["N"], default="N"),
        NmeaFieldDef("arrival", "Arrival Circle Entered", choices=["A","V"], default="V"),
        NmeaFieldDef("perpendicular", "Perpendicular Passed", choices=["A","V"], default="V"),
        NmeaFieldDef("bearing_origin", "Bearing Origin to Destination", units="deg", default="0.0"),
        NmeaFieldDef("bearing_type", "Bearing Type", choices=["M","T"], default="T"),
        NmeaFieldDef("dest_id", "Destination Waypoint ID", default=""),
    ]),

    # --- Time ---
    NmeaSentenceDef("ZDA", "Time & Date - UTC", category="Time", fields=[
        NmeaFieldDef("utc_time", "UTC Time (hhmmss.ss)", default="000000.00"),
        NmeaFieldDef("day", "Day (01-31)", default="01"),
        NmeaFieldDef("month", "Month (01-12)", default="01"),
        NmeaFieldDef("year", "Year (YYYY)", default="2024"),
        NmeaFieldDef("local_tz_hr", "Local Zone Hours (-13 to 13)", default="00"),
        NmeaFieldDef("local_tz_min", "Local Zone Minutes (00 or 30)", default="00"),
    ]),

    # --- RADAR & Tracking ---
    NmeaSentenceDef("TTM", "Tracked Target Message", category="RADAR & Tracking", fields=[
        NmeaFieldDef("target_num", "Target Number (00-99)", default="01"),
        NmeaFieldDef("distance", "Target Distance", units="NM", default="0.0"),
        NmeaFieldDef("bearing", "Bearing from Own Ship", units="deg", default="0.0"),
        NmeaFieldDef("bearing_type", "Bearing Type", choices=["T","R"], default="T"),
        NmeaFieldDef("speed", "Target Speed", units="knots", default="0.0"),
        NmeaFieldDef("course", "Target Course", units="deg", default="0.0"),
        NmeaFieldDef("course_type", "Course Type", choices=["T","R"], default="T"),
        NmeaFieldDef("dist_cpa", "Distance of CPA", units="NM", default="0.0"),
        NmeaFieldDef("time_cpa", "Time to CPA", units="min", default="0.0"),
        NmeaFieldDef("speed_unit", "Speed/Distance Unit", choices=["K","N","S"], default="N"),
        NmeaFieldDef("target_name", "Target Name", default=""),
        NmeaFieldDef("status", "Target Status", choices=["L","Q","T"], default="T"),
        NmeaFieldDef("reference", "Reference Target", choices=["R",""], default=""),
    ]),

    NmeaSentenceDef("TLL", "Target Latitude and Longitude", category="RADAR & Tracking", fields=[
        NmeaFieldDef("target_num", "Target Number", default="01"),
        NmeaFieldDef("latitude", "Latitude", default="0000.00000"),
        NmeaFieldDef("lat_dir", "Latitude Direction", choices=["N","S"], default="N"),
        NmeaFieldDef("longitude", "Longitude", default="00000.00000"),
        NmeaFieldDef("lon_dir", "Longitude Direction", choices=["E","W"], default="E"),
        NmeaFieldDef("target_name", "Target Name", default=""),
        NmeaFieldDef("utc_time", "UTC Time", default=""),
        NmeaFieldDef("status", "Target Status", default=""),
        NmeaFieldDef("reference", "Reference Target", choices=["R",""], default=""),
    ]),

    NmeaSentenceDef("OSD", "Own Ship Data", category="RADAR & Tracking", fields=[
        NmeaFieldDef("heading", "Heading", units="deg", default="0.0"),
        NmeaFieldDef("status", "Status", choices=["A","V"], default="A"),
        NmeaFieldDef("vessel_course", "Vessel Course", units="deg", default="0.0"),
        NmeaFieldDef("course_ref", "Course Reference", choices=["B","M","W","R","P"], default="T"),
        NmeaFieldDef("vessel_speed", "Vessel Speed", units="knots", default="0.0"),
        NmeaFieldDef("speed_ref", "Speed Reference", choices=["B","M","W","R","P"], default="N"),
        NmeaFieldDef("vessel_set", "Vessel Set", units="deg", default=""),
        NmeaFieldDef("vessel_drift", "Vessel Drift", units="knots", default=""),
        NmeaFieldDef("speed_unit", "Speed Unit", choices=["K","N","S"], default="N"),
    ]),

    # --- AIS ---
    NmeaSentenceDef("VDM", "AIS VHF Data-Link Message (other vessels)", category="AIS", fields=[
        NmeaFieldDef("num_msgs", "Total Number of Sentences", default="1"),
        NmeaFieldDef("msg_num", "Sentence Number", default="1"),
        NmeaFieldDef("seq_id", "Sequential Message Identifier", default=""),
        NmeaFieldDef("radio_channel", "Radio Channel", choices=["A","B"], default="A"),
        NmeaFieldDef("payload", "Data Payload (6-bit ASCII encoded)", default=""),
        NmeaFieldDef("fill_bits", "Number of Fill Bits", default="0"),
    ]),

    NmeaSentenceDef("VDO", "AIS VHF Data-Link Own-Vessel Report", category="AIS", fields=[
        NmeaFieldDef("num_msgs", "Total Number of Sentences", default="1"),
        NmeaFieldDef("msg_num", "Sentence Number", default="1"),
        NmeaFieldDef("seq_id", "Sequential Message Identifier", default=""),
        NmeaFieldDef("radio_channel", "Radio Channel", choices=["A","B"], default="A"),
        NmeaFieldDef("payload", "Data Payload (6-bit ASCII encoded)", default=""),
        NmeaFieldDef("fill_bits", "Number of Fill Bits", default="0"),
    ]),
]

# Build a lookup dict for quick access by sentence_id
SENTENCE_LOOKUP: Dict[str, NmeaSentenceDef] = {
    s.sentence_id: s for s in STANDARD_SENTENCES
}

# Unique categories for UI grouping
CATEGORIES: List[str] = sorted(set(s.category for s in STANDARD_SENTENCES))
