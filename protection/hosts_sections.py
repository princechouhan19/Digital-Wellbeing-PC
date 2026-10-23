"""
hosts_sections.py — Shared coordination for Windows hosts-file writers.

Two independent features write their own delimited sections into the hosts
file:
  - Focus Mode website blocking  → "# DIGITAL WELLBEING BLOCK START/END"
  - SafeBrowse content filter    → "# DW-SAFEBROWSE START/END"

Sections use distinct marker formats so neither feature can ever strip the
other's entries. The in-app RLock serializes read-modify-write cycles across
threads; helper processes (UAC elevated) run rarely and only re-add their own
section, so transient interleaving is self-healing.
"""
from __future__ import annotations

import threading

# Serializes hosts read-modify-write across all threads in this process.
HOSTS_LOCK = threading.RLock()

# Marker formats
FOCUS_HEADER = "# DIGITAL WELLBEING BLOCK START"
FOCUS_FOOTER = "# DIGITAL WELLBEING BLOCK END"
CONTENT_HEADER = "# DW-SAFEBROWSE START"
CONTENT_FOOTER = "# DW-SAFEBROWSE END"
