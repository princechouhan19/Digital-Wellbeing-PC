"""
test_updater.py - Automated tests for the updater module.
"""
import pytest
from utils.updater import Updater

def test_compare_versions():
    updater = Updater()
    
    # 0 means equal, -1 means a < b, 1 means a > b
    assert updater._compare_versions("2.5.2", "2.5.2") == 0
    assert updater._compare_versions("v2.5.2", "2.5.2") == 0
    assert updater._compare_versions("2.5.1", "2.5.2") == -1
    assert updater._compare_versions("2.5.2", "2.6.0") == -1
    assert updater._compare_versions("2.5.9", "2.5.10") == -1
    assert updater._compare_versions("2.6.0", "2.5.2") == 1
    assert updater._compare_versions("invalid", "2.5.2") == 1
    assert updater._compare_versions("2.5.2", "invalid") == -1
    assert updater._compare_versions("Unknown", "2.5.2") == -1

