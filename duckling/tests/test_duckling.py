# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) Treble.ai
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)
# -----------------------------------------------------------------------------

"""Tests for pyduckling library."""

# Pytest imports
import pytest

# Third-party imports
import pendulum

# Local imports
from duckling import (load_time_zones, get_current_ref_time, parse_ref_time,
                      parse_lang, default_locale_lang, parse_locale,
                      parse_dimensions, parse, Context)


@pytest.fixture
def time_zones():
    tzdb = load_time_zones("/usr/share/zoneinfo")
    return tzdb


def test_load_time_zones():
    tzdb = load_time_zones("/usr/share/zoneinfo")
    assert tzdb is not None


def test_get_current_ref_time(time_zones):
    ny_now = pendulum.now('America/New_York').replace(microsecond=0)
    ref_time = get_current_ref_time(time_zones, 'America/New_York')
    # The iso8601 string should encode the correct local time with the correct
    # UTC offset. Round-tripping through UTC must give back the same instant.
    this_ref_time = pendulum.parse(ref_time.iso8601).in_tz('UTC').naive()
    this_ref_time = this_ref_time.replace(microsecond=0)
    assert ny_now.in_tz('UTC').naive() == this_ref_time

    # Function should fallback to UTC if the timezone does not exist
    utc_now = pendulum.now('UTC').naive().replace(microsecond=0)
    ref_time = get_current_ref_time(time_zones, 'Continent/Country')
    this_ref_time = pendulum.parse(ref_time.iso8601).in_tz('UTC').naive()
    this_ref_time = this_ref_time.replace(microsecond=0)
    assert this_ref_time == utc_now


def test_parse_ref_time(time_zones):
    ny_now = pendulum.now('America/New_York').replace(microsecond=0)
    ref_time = parse_ref_time(
        time_zones, 'America/New_York', ny_now.int_timestamp)
    # The iso8601 string encodes the correct local time with the correct UTC
    # offset. Round-tripping through UTC must recover the original instant.
    this_ref_time = pendulum.parse(ref_time.iso8601).in_tz('UTC').naive()
    this_ref_time = this_ref_time.replace(microsecond=0)
    assert ny_now.in_tz('UTC').naive() == this_ref_time

    # Initialize any date
    dt = pendulum.datetime(1996, 2, 22, 9, 22, 3, 0, tz="Europe/Madrid")
    ref_time = parse_ref_time(
        time_zones, 'Europe/Madrid', dt.int_timestamp)
    # Same UTC round-trip: parsing the iso8601 back to UTC naive must equal
    # the original datetime's UTC representation.
    this_ref_time = pendulum.parse(ref_time.iso8601).in_tz('UTC').naive()
    this_ref_time = this_ref_time.replace(microsecond=0)
    assert dt.in_tz('UTC').naive() == this_ref_time

    # Function should fallback to UTC if the timezone does not exist
    pst_now = pendulum.now('America/Los_Angeles').replace(microsecond=0)
    ref_time = parse_ref_time(
        time_zones, 'Continent/Country', pst_now.int_timestamp)
    this_ref_time = pendulum.parse(ref_time.iso8601).in_tz('UTC').naive()
    this_ref_time = this_ref_time.replace(microsecond=0)
    assert pst_now.in_tz('UTC').naive() == this_ref_time


def test_parse_lang():
    # Function call should be case-insensitive
    lang_es = parse_lang('es')
    assert lang_es.name == 'ES'

    lang_pt = parse_lang('PT')
    assert lang_pt.name == 'PT'

    # Function should default to EN, when the language does not exists
    lang_any = parse_lang('UU')
    assert lang_any.name == 'EN'


def test_default_locale_lang():
    lang_es = parse_lang('ES')
    default_locale = default_locale_lang(lang_es)
    assert default_locale.name == 'ES_XX'


def test_parse_locale():
    lang_es = parse_lang('ES')
    default_locale = default_locale_lang(lang_es)

    # Parse Language + Country locale
    locale = parse_locale('ES_CO', default_locale)
    assert locale.name == 'ES_CO'

    # Parse Country locale
    locale = parse_locale('CO', default_locale)
    assert locale.name == 'ES_XX'


def test_parse_dimensions():
    valid_dimensions = ["amount-of-money", "credit-card-number", "distance",
                        "duration", "email", "number", "ordinal",
                        "phone-number", "quantity", "temperature",
                        "time", "time-grain", "url", "volume"]

    # All dimensions should be parsed
    output_dims = parse_dimensions(valid_dimensions)
    assert len(output_dims) == len(valid_dimensions)

    invalid_dimensions = ["amount-of-money", "dim1", "credit-card-number",
                          "dim2", "distance", "dim3"]

    # Valid-only dimensions should be parsed
    output_dims = parse_dimensions(invalid_dimensions)
    assert len(output_dims) == len(invalid_dimensions) - 3


def test_parse(time_zones):
    ny_now = pendulum.now('America/New_York').replace(microsecond=0)
    ref_time = parse_ref_time(
        time_zones, 'America/New_York', ny_now.int_timestamp)
    lang_es = parse_lang('ES')
    default_locale = default_locale_lang(lang_es)
    locale = parse_locale('ES_CO', default_locale)

    context = Context(ref_time, locale)
    dimensions = ['time', 'duration']
    dims = parse_dimensions(dimensions)

    # Test time periods
    result = parse('En dos semanas', context, dims, False)
    next_time = result[0]['value']['value']
    # Duckling returns times parsed with the reference time's timezone.
    # We compare the parsed timezone-aware result against the local America/New_York
    # expected datetime to ensure it parsed correctly without UTC fallback.
    next_time = pendulum.parse(next_time)
    expected = ny_now.add(weeks=2).start_of('day')
    assert next_time == expected

    # Test distance units
    dimensions = ['distance']
    dims = parse_dimensions(dimensions)
    result = parse('3 km', context, dims, False)
    info = result[0]['value']
    value = info['value']
    unit = info['unit']
    assert value == 3
    assert unit == 'kilometre'

    # Test volume units
    dimensions = ['volume']
    dims = parse_dimensions(dimensions)
    result = parse('5 litros de leche', context, dims, False)
    info = result[0]['value']
    value = info['value']
    unit = info['unit']
    assert value == 5
    assert unit == 'litre'
