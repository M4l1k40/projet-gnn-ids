"""Reproduce the published CIC-IDS2017 relabelling rules as a sensitivity audit."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.utils.config import load_config

_BATCH_SIZE = 50_000
_NANOSECONDS_PER_MINUTE = 60_000_000_000
_LOCAL_TO_UTC_NS = 3 * 60 * 60 * 1_000_000_000
_TIME_TOLERANCE_NS = 1_000
_ARTIFACT_FLOW_ID = "8.0.6.4-8.6.0.1-0-0-0"

_TUESDAY_FILE = ("Tuesday-WorkingHours.pcap_ISCX.csv",)
_WEDNESDAY_FILE = ("Wednesday-workingHours.pcap_ISCX.csv",)
_THURSDAY_WEB_FILE = ("Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",)
_THURSDAY_INFILTRATION_FILE = (
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
)
_FRIDAY_FILES = (
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    "Friday-WorkingHours-Morning.pcap_ISCX.csv",
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
)
_FRIDAY_PORTSCAN_FILE = ("Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",)
_FRIDAY_DDOS_FILE = ("Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",)
_BOT_SOURCES = ("192.168.10.15", "192.168.10.9", "192.168.10.14", "192.168.10.5", "192.168.10.8")
_WEB_ATTACKER = ("172.16.0.1",)
_WEB_VICTIM = ("192.168.10.50",)
_WEB_XSS_PORTS = (36180, 36182, 36184, 36186, 36188, 36190)
_SQL_PORTS = (36180, 36182, 36184, 36186, 36188)
_HULK_ARTEFACT_PORTS = (48678, 43664)
_SLOWLORIS_ARTEFACT_PORTS = (33358, 33360, 33362, 54114)
_SLOWHTTPTEST_ARTEFACT_PORTS = (33372, 37670)
_PORTSCAN_ARTEFACT_PORTS = (0, 35952, 35954, 35956, 35958)

_TIME_AND_PACKET_COLUMNS = (
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Fwd Packet Length Max",
)


@dataclass(frozen=True)
class _Rule:
    day: str
    label: str
    start_ns: int
    end_ns: int
    source_files: tuple[str, ...]
    source_ips: tuple[str, ...] | None = None
    destination_ips: tuple[str, ...] | None = None
    source_ports: tuple[int, ...] | None = None
    destination_ports: tuple[int, ...] | None = None
    checks: tuple[tuple[str, str, Any], ...] = ()
    any_checks: tuple[tuple[str, str, Any], ...] = ()
    none_checks: tuple[tuple[tuple[str, str, Any], ...], ...] = ()
    attempted_category: int = -1
    flip_direction: bool = False
    payload_filter: bool = False


def _rule(
    day: str,
    label: str,
    start_ns: int,
    end_ns: int,
    source_files: tuple[str, ...],
    *,
    source_ips: tuple[str, ...] | None = None,
    destination_ips: tuple[str, ...] | None = None,
    source_ports: tuple[int, ...] | None = None,
    destination_ports: tuple[int, ...] | None = None,
    checks: tuple[tuple[str, str, Any], ...] = (),
    any_checks: tuple[tuple[str, str, Any], ...] = (),
    none_checks: tuple[tuple[tuple[str, str, Any], ...], ...] = (),
    attempted_category: int = -1,
    flip_direction: bool = False,
    payload_filter: bool = False,
) -> _Rule:
    return _Rule(
        day=day,
        label=label,
        start_ns=start_ns,
        end_ns=end_ns,
        source_files=source_files,
        source_ips=source_ips,
        destination_ips=destination_ips,
        source_ports=source_ports,
        destination_ports=destination_ports,
        checks=checks,
        any_checks=any_checks,
        none_checks=none_checks,
        attempted_category=attempted_category,
        flip_direction=flip_direction,
        payload_filter=payload_filter,
    )


# Independently encoded from Liu, Engelen et al. (CNS 2022) rules, which are
# also cross-referenced with Lanvin et al. (CRiSIS 2022); no source code is copied.
_RULES = (
    _rule("Tuesday", "FTP-Patator", 1499170672838272000, 1499174416931403000, _TUESDAY_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM, destination_ports=(21,), flip_direction=True),
    _rule("Tuesday", "FTP-Patator - Attempted", 1499170672838272000, 1499174416931403000, _TUESDAY_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM, destination_ports=(21,), attempted_category=0,
          payload_filter=True, flip_direction=True),
    _rule("Tuesday", "FTP-Patator - Attempted", 1499170672838272000, 1499174416931403000, _TUESDAY_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM, source_ports=(52108,), destination_ports=(21,),
          attempted_category=2),
    _rule("Tuesday", "FTP-Patator - Attempted", 1499170672838272000, 1499174416931403000, _TUESDAY_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM, destination_ports=(21,),
          checks=(("src_port", "ne", 52108), ("Total Length of Bwd Packets", "eq", 0),
                  ("Total Length of Fwd Packets", "gt", 0)), attempted_category=3),
    _rule("Tuesday", "FTP-Patator - Attempted", 1499170672838272000, 1499174416931403000, _TUESDAY_FILE,
          source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(21,),
          checks=(("dst_port", "ne", 52108), ("Total Length of Fwd Packets", "eq", 0),
                  ("Total Length of Bwd Packets", "gt", 0)), attempted_category=3),
    _rule("Tuesday", "SSH-Patator", 1499188141049616000, 1499195059018486000, _TUESDAY_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM, destination_ports=(22,), flip_direction=True),
    _rule("Tuesday", "SSH-Patator - Attempted", 1499188141049616000, 1499195059018486000, _TUESDAY_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM, destination_ports=(22,),
          attempted_category=0, payload_filter=True, flip_direction=True),
    _rule("Tuesday", "SSH-Patator - Attempted", 1499188141049616000, 1499195059018486000, _TUESDAY_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM, destination_ports=(22,),
          checks=(("Total Fwd Packets", "le", 32), ("Total Length of Bwd Packets", "eq", 0)),
          attempted_category=3),

    _rule("Wednesday", "DoS Slowloris - Attempted", 1499258926211817000, 1499258927000000000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), attempted_category=5),
    _rule("Wednesday", "DoS Slowloris", 1499258934539220000, 1499260278500956000, _WEDNESDAY_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM, destination_ports=(80,),
          checks=(("src_port", "not_in", _SLOWLORIS_ARTEFACT_PORTS),)),
    _rule("Wednesday", "DoS Slowloris", 1499258934539220000, 1499260278500956000, _WEDNESDAY_FILE,
          source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(80,),
          checks=(("dst_port", "not_in", _SLOWLORIS_ARTEFACT_PORTS),)),
    _rule("Wednesday", "DoS Slowloris - Attempted", 1499258934539220000, 1499260278500956000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          source_ports=(33358, 33360, 33362), destination_ports=(80,), attempted_category=2),
    _rule("Wednesday", "DoS Slowloris - Attempted", 1499258934539220000, 1499260278500956000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("src_port", "not_in", (33358, 33360, 33362, 54114)),),
          attempted_category=0, payload_filter=True),
    _rule("Wednesday", "DoS Slowloris - Attempted", 1499258934539220000, 1499260278500956000,
          _WEDNESDAY_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(80,),
          checks=(("dst_port", "not_in", _SLOWLORIS_ARTEFACT_PORTS),
                  ("Total Length of Bwd Packets", "eq", 0)), attempted_category=0),
    _rule("Wednesday", "DoS Slowloris - Attempted", 1499258934539220000, 1499260278500956000,
          _WEDNESDAY_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(80,),
          checks=(("dst_port", "not_in", _SLOWLORIS_ARTEFACT_PORTS),
                  ("Total Length of Bwd Packets", "eq", 0), ("Flow Duration", "ge", 199800)),
          attempted_category=6),
    _rule("Wednesday", "DoS Slowloris - Attempted", 1499258934539220000, 1499260278500956000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          source_ports=(54114,), destination_ports=(80,), attempted_category=4),

    _rule("Wednesday", "DoS Slowhttptest", 1499260537936810000, 1499261869331517000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("src_port", "not_in", (33372,)),)),
    _rule("Wednesday", "DoS Slowhttptest", 1499260537936810000, 1499261869331517000,
          _WEDNESDAY_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(80,),
          checks=(("dst_port", "not_in", (33372,)),)),
    _rule("Wednesday", "DoS Slowhttptest - Attempted", 1499260537936810000, 1499261869331517000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          source_ports=(33372,), destination_ports=(80,), attempted_category=2),
    _rule("Wednesday", "DoS Slowhttptest - Attempted", 1499260537936810000, 1499261869331517000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("src_port", "not_in", _SLOWHTTPTEST_ARTEFACT_PORTS),),
          attempted_category=0, payload_filter=True),
    _rule("Wednesday", "DoS Slowhttptest - Attempted", 1499260537936810000, 1499261869331517000,
          _WEDNESDAY_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(80,),
          checks=(("dst_port", "not_in", _SLOWHTTPTEST_ARTEFACT_PORTS),
                  ("Total Length of Bwd Packets", "eq", 0)), attempted_category=0),
    _rule("Wednesday", "DoS Slowhttptest - Attempted", 1499260537936810000, 1499261869331517000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("src_port", "ne", 33372),
                  ("Total Length of Fwd Packets", "eq", 0), ("Flow Duration", "ge", 199984),
                  ("Total Backward Packets", "eq", 0)), attempted_category=6),
    _rule("Wednesday", "DoS Slowhttptest - Attempted", 1499260537936810000, 1499261869331517000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          source_ports=(37670,), destination_ports=(80,), attempted_category=4),

    _rule("Wednesday", "DoS Hulk", 1499262203194704000, 1499262299999999999,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("src_port", "not_in", _HULK_ARTEFACT_PORTS),)),
    _rule("Wednesday", "DoS Hulk", 1499262203194704000, 1499262299999999999,
          _WEDNESDAY_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(80,),
          checks=(("dst_port", "not_in", _HULK_ARTEFACT_PORTS),)),
    _rule("Wednesday", "DoS Hulk", 1499262300000000000, 1499263641326171000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), flip_direction=True),
    _rule("Wednesday", "DoS Hulk - Attempted", 1499262203194704000, 1499262299999999999,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          source_ports=_HULK_ARTEFACT_PORTS, destination_ports=(80,), attempted_category=4),
    _rule("Wednesday", "DoS Hulk - Attempted", 1499262203194704000, 1499263641326171000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("src_port", "not_in", _HULK_ARTEFACT_PORTS),),
          attempted_category=0, payload_filter=True),
    _rule("Wednesday", "DoS Hulk - Attempted", 1499262203194704000, 1499263641326171000,
          _WEDNESDAY_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(80,),
          checks=(("dst_port", "not_in", _HULK_ARTEFACT_PORTS),
                  ("Total Length of Bwd Packets", "eq", 0)), attempted_category=0),
    _rule("Wednesday", "DoS Hulk - Attempted", 1499262203194704000, 1499263641326171000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("src_port", "not_in", _HULK_ARTEFACT_PORTS),
                  ("Total Length of Fwd Packets", "gt", 0),
                  ("Total Length of Fwd Packets", "lt", 282)), attempted_category=3),
    _rule("Wednesday", "DoS Hulk - Attempted", 1499262203194704000, 1499263641326171000,
          _WEDNESDAY_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(80,),
          checks=(("dst_port", "not_in", _HULK_ARTEFACT_PORTS),
                  ("Total Length of Bwd Packets", "gt", 0),
                  ("Total Length of Bwd Packets", "lt", 282)), attempted_category=3),

    _rule("Wednesday", "DoS GoldenEye", 1499263803231753000, 1499264408915718000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), flip_direction=True),
    _rule("Wednesday", "DoS GoldenEye - Attempted", 1499263803231753000, 1499264408915718000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), attempted_category=0, payload_filter=True, flip_direction=True),
    _rule("Wednesday", "Heartbleed", 1499278335650811000, 1499279563294455000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=("192.168.10.51",),
          source_ports=(45022,), destination_ports=(444,), flip_direction=True),
    _rule("Wednesday", "Heartbleed - Attempted", 1499278335650811000, 1499279563294455000,
          _WEDNESDAY_FILE, source_ips=_WEB_ATTACKER, destination_ips=("192.168.10.51",),
          source_ports=(45022,), destination_ports=(444,), attempted_category=0,
          payload_filter=True, flip_direction=True),

    _rule("Thursday", "Web Attack - Brute Force - Attempted", 1499343354880049000, 1499343531179279000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), attempted_category=2, flip_direction=True),
    _rule("Thursday", "Web Attack - Brute Force", 1499343567660566000, 1499346011622209000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), any_checks=(("Total Fwd Packets", "gt", 20),
                                               ("src_port", "eq", 44464))),
    _rule("Thursday", "Web Attack - Brute Force", 1499343567660566000, 1499346011622209000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER,
          source_ports=(80,), any_checks=(("Total Backward Packets", "gt", 20),
                                          ("dst_port", "eq", 44464))),
    _rule("Thursday", "Web Attack - Brute Force - Attempted", 1499343567660566000, 1499346011622209000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("Total Fwd Packets", "le", 20), ("src_port", "ne", 44464)),
          attempted_category=0, payload_filter=True),
    _rule("Thursday", "Web Attack - Brute Force - Attempted", 1499343567660566000, 1499346011622209000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(80,),
          checks=(("Total Backward Packets", "le", 20), ("dst_port", "ne", 44464),
                  ("Total Length of Bwd Packets", "eq", 0)), attempted_category=0),
    _rule("Thursday", "Web Attack - Brute Force - Attempted", 1499343567660566000, 1499346011622209000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("Total Length of Fwd Packets", "gt", 0),
                  ("src_port", "ne", 44464), ("Total Fwd Packets", "eq", 4),
                  ("Total Backward Packets", "eq", 4)), attempted_category=4),
    _rule("Thursday", "Web Attack - Brute Force - Attempted", 1499343567660566000, 1499346011622209000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(80,),
          checks=(("Total Length of Bwd Packets", "gt", 0), ("dst_port", "ne", 44464),
                  ("Total Backward Packets", "eq", 4), ("Total Fwd Packets", "eq", 4)),
          attempted_category=4),

    _rule("Thursday", "Web Attack - XSS", 1499346935283859000, 1499348121341704000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("src_port", "not_in", _WEB_XSS_PORTS),
                                          ("Total Fwd Packets", "ge", 150))),
    _rule("Thursday", "Web Attack - XSS", 1499346935283859000, 1499348121341704000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER,
          source_ports=(80,), checks=(("dst_port", "not_in", _WEB_XSS_PORTS),
                                     ("Total Backward Packets", "ge", 150))),
    _rule("Thursday", "Web Attack - XSS - Attempted", 1499346935283859000, 1499348121341704000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("src_port", "not_in", _WEB_XSS_PORTS),),
          attempted_category=0, payload_filter=True),
    _rule("Thursday", "Web Attack - XSS - Attempted", 1499346935283859000, 1499348121341704000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER,
          source_ports=(80,), checks=(("dst_port", "not_in", _WEB_XSS_PORTS),
                                     ("Total Length of Bwd Packets", "eq", 0)), attempted_category=0),
    _rule("Thursday", "Web Attack - XSS - Attempted", 1499346935283859000, 1499348121341704000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("src_port", "not_in", _WEB_XSS_PORTS),
                  ("Total Length of Fwd Packets", "gt", 0), ("Total Fwd Packets", "lt", 150)),
          attempted_category=2),
    _rule("Thursday", "Web Attack - XSS - Attempted", 1499346935283859000, 1499348121341704000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(80,),
          checks=(("dst_port", "not_in", _WEB_XSS_PORTS),
                  ("Total Length of Bwd Packets", "gt", 0), ("Total Backward Packets", "lt", 150)),
          attempted_category=2),

    _rule("Thursday", "Web Attack - SQL Injection - Attempted", 1499348127852814000, 1499348145720612000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("src_port", "in", _SQL_PORTS),), attempted_category=2),
    _rule("Thursday", "Web Attack - SQL Injection - Attempted", 1499348127852814000, 1499348145720612000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER,
          source_ports=(80,), checks=(("dst_port", "in", _SQL_PORTS),), attempted_category=2),
    _rule("Thursday", "Web Attack - SQL Injection", 1499348145732950000, 1499348575320284000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), checks=(("src_port", "not_in", _SQL_PORTS),)),
    _rule("Thursday", "Web Attack - SQL Injection", 1499348145732950000, 1499348575320284000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER, source_ports=(80,),
          checks=(("dst_port", "not_in", _SQL_PORTS),)),
    _rule("Thursday", "Web Attack - SQL Injection - Attempted", 1499348127852814000, 1499348145720612000,
          _THURSDAY_WEB_FILE, source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          destination_ports=(80,), attempted_category=0, payload_filter=True, flip_direction=True),

    _rule("Thursday", "Infiltration", 1499361542547210000, 1499366769364731000,
          _THURSDAY_INFILTRATION_FILE, source_ips=("192.168.10.8",),
          destination_ips=("205.174.165.73",), flip_direction=True),
    _rule("Thursday", "Infiltration - Attempted", 1499361542547210000, 1499366769364731000,
          _THURSDAY_INFILTRATION_FILE, source_ips=("192.168.10.8",),
          destination_ips=("205.174.165.73",), attempted_category=0,
          payload_filter=True, flip_direction=True),
    _rule("Thursday", "Infiltration - Attempted", 1499361228830533000, 1499361301251276000,
          _THURSDAY_INFILTRATION_FILE, source_ips=("192.168.10.9",),
          destination_ips=("205.174.165.73",), attempted_category=2, flip_direction=True),
    _rule("Thursday", "Infiltration", 1499363616453990000, 1499371339347892000,
          _THURSDAY_INFILTRATION_FILE, source_ips=("192.168.10.25",),
          destination_ips=("205.174.165.73",), flip_direction=True),
    _rule("Thursday", "Infiltration - Attempted", 1499363616453990000, 1499371339347892000,
          _THURSDAY_INFILTRATION_FILE, source_ips=("192.168.10.25",),
          destination_ips=("205.174.165.73",), attempted_category=0,
          payload_filter=True, flip_direction=True),
    _rule("Thursday", "Infiltration - Portscan", 1499360400000000000, 1499360460000000000,
          _THURSDAY_INFILTRATION_FILE, source_ips=_WEB_ATTACKER,
          destination_ips=("192.168.10.51",), checks=(("src_port", "eq", 50122),)),
    _rule("Thursday", "Infiltration - Portscan", 1499362410884008000, 1499362444285175000,
          _THURSDAY_INFILTRATION_FILE, source_ips=("192.168.10.8",),
          destination_ips=("192.168.10.5",)),
    _rule("Thursday", "Infiltration - Portscan", 1499364314425162000, 1499366764331875000,
          _THURSDAY_INFILTRATION_FILE, source_ips=("192.168.10.8",),
          destination_ips=("192.168.10.5", "192.168.10.9", "192.168.10.12", "192.168.10.14",
                           "192.168.10.15", "192.168.10.16", "192.168.10.17", "192.168.10.19",
                           "192.168.10.25", "192.168.10.50", "192.168.10.51"),
          none_checks=((("Fwd Packet Length Max", "eq", 408),
                        ("dst_ip", "eq", "192.168.10.50")),
                       (("Total Length of Fwd Packets", "in", (176, 20514)),
                        ("dst_ip", "eq", "192.168.10.50")))),

    _rule("Friday", "Portscan", 1499446532117090000, 1499447948582083000, _FRIDAY_PORTSCAN_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM, flip_direction=True),
    _rule("Friday", "Portscan", 1499449860000000000, 1499449919000000000, _FRIDAY_PORTSCAN_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM,
          checks=(("src_port", "not_in", _PORTSCAN_ARTEFACT_PORTS),)),
    _rule("Friday", "Portscan", 1499449920000000000, 1499451841699238000, _FRIDAY_PORTSCAN_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM),

    _rule("Friday", "Botnet", 1499432653990571000, 1499436122903736000, _FRIDAY_FILES,
          source_ips=_BOT_SOURCES, destination_ips=("205.174.165.73",), flip_direction=True),
    _rule("Friday", "Botnet - Attempted", 1499432653990571000, 1499436122903736000, _FRIDAY_FILES,
          source_ips=_BOT_SOURCES, destination_ips=("205.174.165.73",), attempted_category=0,
          payload_filter=True, flip_direction=True),
    _rule("Friday", "Botnet - Attempted", 1499436180000000000, 1499457684606663000, _FRIDAY_FILES,
          source_ips=_BOT_SOURCES, destination_ips=("205.174.165.73",), attempted_category=1,
          flip_direction=True),

    _rule("Friday", "DDoS", 1499453791796937000, 1499454972216560000, _FRIDAY_DDOS_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM, flip_direction=True),
    _rule("Friday", "DDoS - Attempted", 1499453791796937000, 1499454972216560000, _FRIDAY_DDOS_FILE,
          source_ips=_WEB_ATTACKER, destination_ips=_WEB_VICTIM, attempted_category=0,
          payload_filter=True, flip_direction=True),
    _rule("Friday", "DDoS - Attempted", 1499453791796937000, 1499454972216560000, _FRIDAY_DDOS_FILE,
          source_ips=_WEB_VICTIM, destination_ips=_WEB_ATTACKER,
          checks=(("Total Length of Bwd Packets", "eq", 0),), attempted_category=0),

    _rule("Friday", "Botnet", 1499432653990571000, 1499436122903736000, _FRIDAY_DDOS_FILE,
          source_ips=_BOT_SOURCES, destination_ips=("205.174.165.73",), flip_direction=True),
    _rule("Friday", "Botnet - Attempted", 1499432653990571000, 1499436122903736000, _FRIDAY_DDOS_FILE,
          source_ips=_BOT_SOURCES, destination_ips=("205.174.165.73",), attempted_category=0,
          payload_filter=True, flip_direction=True),
    _rule("Friday", "Botnet - Attempted", 1499436180000000000, 1499457684606663000, _FRIDAY_DDOS_FILE,
          source_ips=_BOT_SOURCES, destination_ips=("205.174.165.73",), attempted_category=1,
          flip_direction=True),
)


def _flow_start_utc_ns(frame: pd.DataFrame) -> np.ndarray:
    """Derive UTC start times from local-as-UTC ts_end and microsecond durations."""
    end_seconds = pd.to_numeric(frame["ts_end"], errors="coerce").to_numpy(
        dtype=np.float64,
        na_value=np.nan,
    )
    duration_us = pd.to_numeric(frame["Flow Duration"], errors="coerce").to_numpy(
        dtype=np.float64,
        na_value=np.nan,
    )
    invalid = ~np.isfinite(end_seconds) | ~np.isfinite(duration_us)
    if invalid.any():
        raise ValueError(
            f"ts_end/Flow Duration : {int(invalid.sum())} valeur(s) absente(s) ou non finie(s)."
        )
    return (
        np.rint(end_seconds * 1_000_000_000).astype(np.int64)
        - np.rint(duration_us * 1_000).astype(np.int64)
        + _LOCAL_TO_UTC_NS
    )


def _comparison(values: pd.Series, operator: str, expected: Any) -> pd.Series:
    if operator == "eq":
        return values.eq(expected)
    if operator == "ne":
        return values.ne(expected)
    if operator == "gt":
        return values.gt(expected)
    if operator == "ge":
        return values.ge(expected)
    if operator == "lt":
        return values.lt(expected)
    if operator == "le":
        return values.le(expected)
    if operator == "in":
        return values.isin(expected)
    if operator == "not_in":
        return ~values.isin(expected)
    raise ValueError(f"Opérateur de règle inconnu : {operator}.")


def _direction_mask(
    frame: pd.DataFrame,
    start_times_utc_ns: np.ndarray,
    rule: _Rule,
    *,
    reverse: bool,
) -> np.ndarray:
    start_floor_ns = rule.start_ns - rule.start_ns % _NANOSECONDS_PER_MINUTE
    mask = (
        (frame["day"].astype(str).to_numpy() == rule.day)
        & frame["source_file"].astype(str).isin(rule.source_files).to_numpy()
        & (start_times_utc_ns + _TIME_TOLERANCE_NS >= start_floor_ns)
        & (start_times_utc_ns <= rule.end_ns + _TIME_TOLERANCE_NS)
    )
    source_column, destination_column = (
        ("dst_ip", "src_ip") if reverse else ("src_ip", "dst_ip")
    )
    source_port_column, destination_port_column = (
        ("dst_port", "src_port") if reverse else ("src_port", "dst_port")
    )
    if rule.source_ips is not None:
        mask &= frame[source_column].isin(rule.source_ips).to_numpy()
    if rule.destination_ips is not None:
        mask &= frame[destination_column].isin(rule.destination_ips).to_numpy()
    if rule.source_ports is not None:
        mask &= frame[source_port_column].isin(rule.source_ports).to_numpy()
    if rule.destination_ports is not None:
        mask &= frame[destination_port_column].isin(rule.destination_ports).to_numpy()
    for column, operator, expected in rule.checks:
        mask &= _comparison(frame[column], operator, expected).to_numpy()
    if rule.any_checks:
        any_mask = np.zeros(len(frame), dtype=bool)
        for column, operator, expected in rule.any_checks:
            any_mask |= _comparison(frame[column], operator, expected).to_numpy()
        mask &= any_mask
    for rejected_group in rule.none_checks:
        rejected = np.ones(len(frame), dtype=bool)
        for column, operator, expected in rejected_group:
            rejected &= _comparison(frame[column], operator, expected).to_numpy()
        mask &= ~rejected
    if rule.payload_filter:
        payload_column = (
            "Total Length of Bwd Packets" if reverse else "Total Length of Fwd Packets"
        )
        mask &= frame[payload_column].eq(0).to_numpy()
    return mask


def _rule_mask(
    frame: pd.DataFrame,
    start_times_utc_ns: np.ndarray,
    rule: _Rule,
) -> np.ndarray:
    mask = _direction_mask(frame, start_times_utc_ns, rule, reverse=False)
    if rule.flip_direction:
        mask |= _direction_mask(frame, start_times_utc_ns, rule, reverse=True)
    return mask


def _report_tables(
    counts: Counter[tuple[str, str, str]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    records: list[dict[str, Any]] = []
    totals_by_day_label: Counter[tuple[str, str]] = Counter()
    changed_by_day_label: Counter[tuple[str, str]] = Counter()
    changed_by_label: Counter[str] = Counter()
    totals_by_label: Counter[str] = Counter()
    attacks_to_benign: Counter[tuple[str, str]] = Counter()
    attacks_to_attempted: Counter[tuple[str, str]] = Counter()
    benign_to_attack: Counter[tuple[str, str]] = Counter()

    for (day, original, rule_label), count in sorted(counts.items()):
        records.append(
            {
                "day": day,
                "label_multi": original,
                "label_rule": rule_label,
                "flows": count,
            }
        )
        totals_by_day_label[(day, original)] += count
        totals_by_label[original] += count
        changed = original != rule_label
        if changed:
            changed_by_day_label[(day, original)] += count
            changed_by_label[original] += count
        if original != "BENIGN" and rule_label == "BENIGN":
            attacks_to_benign[(day, original)] += count
        if original != "BENIGN" and rule_label.endswith(" - Attempted"):
            attacks_to_attempted[(day, original)] += count
        if original == "BENIGN" and rule_label != "BENIGN":
            benign_to_attack[(day, rule_label)] += count

    matrix = pd.DataFrame.from_records(records)
    if not matrix.empty:
        matrix["original_day_total"] = [
            totals_by_day_label[(row.day, row.label_multi)]
            for row in matrix.itertuples(index=False)
        ]
        matrix["pct_of_original_day_class"] = (
            100 * matrix["flows"] / matrix["original_day_total"]
        )

    class_records = [
        {
            "label_multi": label,
            "flows": totals_by_label[label],
            "different_flows": changed_by_label[label],
            "different_pct": 100 * changed_by_label[label] / totals_by_label[label],
            "class_share_pct": 100 * totals_by_label[label] / sum(totals_by_label.values()),
        }
        for label in sorted(totals_by_label)
    ]
    class_summary = pd.DataFrame.from_records(class_records)
    attack_records = [
        {
            "day": day,
            "label_multi": label,
            "attacks_to_benign": attacks_to_benign[(day, label)],
            "attacks_to_attempted": attacks_to_attempted[(day, label)],
        }
        for day, label in sorted(set(attacks_to_benign) | set(attacks_to_attempted))
    ]
    benign_records = [
        {"day": day, "label_rule": label, "benign_to_attack": count}
        for (day, label), count in sorted(benign_to_attack.items())
    ]
    return (
        matrix,
        class_summary,
        pd.DataFrame.from_records(attack_records),
        pd.DataFrame.from_records(benign_records),
    )


def _write_report(
    report_path: Path,
    csv_path: Path,
    matrix: pd.DataFrame,
    class_summary: pd.DataFrame,
    attack_changes: pd.DataFrame,
    benign_changes: pd.DataFrame,
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(csv_path, index=False, encoding="utf-8")
    lines = [
        "# Audit de sensibilité des labels CIC-IDS2017",
        "",
        "Cet audit réapplique, à titre d’analyse, les règles publiées par Liu, Engelen et al. "
        "(CNS 2022), en tenant compte des travaux de Lanvin et al. (CRiSIS 2022). "
        "Il ne modifie ni `label_multi` ni les Parquets finaux.",
        "",
        "## Méthode et fuseau horaire",
        "",
        "- Les règles du notebook définissent des fenêtres UTC et s’appliquent à l’heure de début du flux.",
        "- `clean.parquet` stocke `ts_end` comme epoch en secondes à partir de l’heure locale naïve. "
        "Le début est calculé par `ts_end - Flow Duration / 1e6`, puis on ajoute 3 h pour UTC.",
        "- Contrôle simple : 4 juillet 2017, 10:00 heure locale devient 13:00 UTC.",
        "- Le début de chaque fenêtre est arrondi à la minute inférieure, comme dans la règle publiée; "
        "la borne de fin est inclusive.",
        "- Les appels sont appliqués dans leur ordre d’origine : les catégories Attempted et filtres de "
        "paquets peuvent donc remplacer une règle antérieure.",
        "- Le lundi ne comporte pas de bloc d’attaque explicite dans le notebook consulté : ses flux "
        "restent BENIGN selon la règle de repli.",
        "",
        "## Matrice par jour : label d’origine × règle",
        "",
        "Le pourcentage indique la part de la classe d’origine de ce jour attribuée à cette règle.",
        "",
        "| Jour | label_multi d’origine | label_rule | Flux | Part de la classe d’origine |",
        "|---|---|---|---:|---:|",
    ]
    for row in matrix.itertuples(index=False):
        lines.append(
            f"| {row.day} | {row.label_multi} | {row.label_rule} | {row.flows} | "
            f"{row.pct_of_original_day_class:.4f} % |"
        )
    lines.extend(
        [
            "",
            "## Flux d’attaque d’origine réattribués à BENIGN ou Attempted",
            "",
            "| Jour | label_multi d’origine | Vers BENIGN | Vers Attempted |",
            "|---|---|---:|---:|",
        ]
    )
    for row in attack_changes.itertuples(index=False):
        lines.append(
            f"| {row.day} | {row.label_multi} | {row.attacks_to_benign} | "
            f"{row.attacks_to_attempted} |"
        )
    lines.extend(
        [
            "",
            "## Flux BENIGN d’origine réattribués à une attaque",
            "",
            "| Jour | label_rule | Flux |",
            "|---|---|---:|",
        ]
    )
    for row in benign_changes.itertuples(index=False):
        lines.append(f"| {row.day} | {row.label_rule} | {row.benign_to_attack} |")
    lines.extend(
        [
            "",
            "## Part des classes et différences exactes",
            "",
            "Une différence est comptée lorsque `label_rule` diffère textuellement de `label_multi`; "
            "les différences de casse ou de nomenclature sont donc visibles dans cette sensibilité.",
            "",
            "| Classe d’origine | Flux | Part du jeu | Différents | Part différente |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in class_summary.itertuples(index=False):
        lines.append(
            f"| {row.label_multi} | {row.flows} | {row.class_share_pct:.4f} % | "
            f"{row.different_flows} | {row.different_pct:.4f} % |"
        )
    lines.extend(
        [
            "",
            "## Règles non reproduites et limites",
            "",
            "- Le notebook consulté ne contient pas de bloc d’attaque pour Monday; la convention "
            "de repli BENIGN est appliquée, mais aucune règle Monday spécifique n’est inférée.",
            "- L’audit part du Parquet nettoyé et de son `ts_end`; il ne rejoue pas le parseur CSV "
            "historique du notebook, dont le seuil de reconstruction AM/PM était différent "
            "(heure < 7 contre le seuil 8 de la configuration courante). Les règles de fenêtres, "
            "IP, ports et filtres sont appliquées aux timestamps disponibles; les cas de bord à 07:xx "
            "ne peuvent pas être garantis identiques à cette ancienne étape de parsing.",
            "- Les catégories de flux Attempted sont émises avec leur règle, mais ne sont pas "
            "interprétées comme une correction de label.",
            "- Cet audit ne corrige PAS les erreurs d’extraction de flux (paquets mal ordonnés ou "
            "dupliqués) : les vérifier exige les PCAP et un CICFlowMeter modifié.",
            "",
            f"CSV détaillé : `{csv_path.name}`.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_label_audit(
    config: dict[str, Any] | None = None,
    *,
    input_path: str | Path | None = None,
    output_path: str | Path | None = None,
    report_path: str | Path | None = None,
    csv_path: str | Path | None = None,
    batch_size: int = _BATCH_SIZE,
) -> tuple[Path, Path, Path, pd.DataFrame]:
    """Generate the relabelling audit without modifying original labels."""
    project_config = load_config() if config is None else config
    paths = project_config["paths"]
    interim_dir = Path(paths["interim"])
    processed_dir = Path(paths["processed"])
    project_root = processed_dir.parent.parent
    source_path = Path(input_path) if input_path is not None else interim_dir / "clean.parquet"
    audit_path = (
        Path(output_path) if output_path is not None else processed_dir / "label_audit.parquet"
    )
    output_report = (
        Path(report_path) if report_path is not None else project_root / "reports" / "label_audit.md"
    )
    output_csv = (
        Path(csv_path) if csv_path is not None else project_root / "reports" / "label_audit.csv"
    )
    if batch_size < 1:
        raise ValueError("batch_size doit être supérieur à zéro.")
    if not source_path.exists():
        raise FileNotFoundError(f"Parquet nettoyé introuvable : {source_path}.")
    source = pq.ParquetFile(source_path)
    required = {
        "flow_id",
        "orig_flow_id",
        "day",
        "source_file",
        "src_ip",
        "dst_ip",
        "src_port",
        "dst_port",
        "Flow Duration",
        "ts_end",
        "label_multi",
        *_TIME_AND_PACKET_COLUMNS,
    }
    missing = required - set(source.schema_arrow.names)
    if missing:
        raise ValueError(
            "Colonnes requises absentes de clean.parquet : "
            + ", ".join(sorted(missing))
            + "."
        )
    columns = [
        "flow_id",
        "orig_flow_id",
        "day",
        "source_file",
        "src_ip",
        "dst_ip",
        "src_port",
        "dst_port",
        "Flow Duration",
        "ts_end",
        "label_multi",
        *_TIME_AND_PACKET_COLUMNS,
    ]
    columns = list(dict.fromkeys(columns))
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter[tuple[str, str, str]] = Counter()
    writer: pq.ParquetWriter | None = None
    try:
        for batch in source.iter_batches(columns=columns, batch_size=batch_size):
            frame = batch.to_pandas()
            if frame[["flow_id", "label_multi", "day", "source_file"]].isna().any().any():
                raise ValueError("clean.parquet contient des identifiants, labels ou jours manquants.")
            start_times = _flow_start_utc_ns(frame)
            labels = np.full(len(frame), "BENIGN", dtype=object)
            categories = np.full(len(frame), -1, dtype=np.int8)
            for rule in _RULES:
                matched = _rule_mask(frame, start_times, rule)
                labels[matched] = rule.label
                categories[matched] = rule.attempted_category
            artefact = frame["orig_flow_id"].astype(str).eq(_ARTIFACT_FLOW_ID).to_numpy()
            labels[artefact] = "BENIGN"
            categories[artefact] = -1

            original = frame["label_multi"].astype(str).to_numpy()
            days = frame["day"].astype(str).to_numpy()
            for day, original_label, rule_label in zip(days, original, labels):
                counts[(day, original_label, str(rule_label))] += 1
            output = pd.DataFrame(
                {
                    "flow_id": frame["flow_id"].astype("string"),
                    "label_rule": pd.Series(labels, dtype="string"),
                    "attempted_category": categories,
                }
            )
            table = pa.Table.from_pandas(output, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(audit_path, table.schema)
            else:
                table = table.cast(writer.schema)
            writer.write_table(table, row_group_size=batch_size)
    finally:
        if writer is not None:
            writer.close()

    if writer is None:
        raise ValueError(f"Parquet source vide : {source_path}.")
    if pq.ParquetFile(audit_path).metadata.num_rows != source.metadata.num_rows:
        raise ValueError("Le nombre de lignes de l’audit ne correspond pas à clean.parquet.")

    matrix, class_summary, attack_changes, benign_changes = _report_tables(counts)
    _write_report(
        output_report,
        output_csv,
        matrix,
        class_summary,
        attack_changes,
        benign_changes,
    )
    difference_total = int(class_summary["different_flows"].sum())
    row_total = int(class_summary["flows"].sum())
    print(
        f"Label audit: {difference_total}/{row_total} flux diffèrent du label d’origine "
        f"({100 * difference_total / row_total:.4f} %)."
    )
    print(
        class_summary[
            ["label_multi", "flows", "different_flows", "different_pct"]
        ].to_string(index=False)
    )
    return audit_path, output_report, output_csv, class_summary


if __name__ == "__main__":
    build_label_audit()
