#! /usr/bin/env python
#
#  -*- mode: python; -*-
#
"""
Script to snarf nominal and real rates from the Treasury Department site
and output in CSV format.
"""
import datetime
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from dataclasses import dataclass
from enum import Enum
import decimal  # for getcontext()
from decimal import Decimal

import requests


class RatesType(Enum):
    """Used to distinguish nominal vs real rates."""

    NOMINAL = "BC_"  # use US Treasury prefixes
    REAL = "TC_"


@dataclass(frozen=True)
class Rates:
    """Class representing a particular set of treasury yields."""

    rt: RatesType
    date: str
    r5y: Decimal
    r10y: Decimal
    r20y: Decimal
    r30y: Decimal

    def print_as_csv(self):
        """Output a rates as CSV text."""
        prefix = self.rt.value
        print("NAME,VALUE")
        print(f"NEW_DATE,{self.date}")
        print(f"{prefix}5YEAR,{self.r5y}")
        print(f"{prefix}10YEAR,{self.r10y}")
        print(f"{prefix}20YEAR,{self.r20y}")
        print(f"{prefix}30YEAR,{self.r30y}")


TREASURY_RATE_XML_URL = (
    "https://home.treasury.gov/"
    + "resource-center/data-chart-center/interest-rates/pages/xml"
)
DATA_NAME = "data"
NOMINAL_DATA_VALUE = "daily_treasury_yield_curve"
REAL_DATA_VALUE = "daily_treasury_real_yield_curve"
DATE_VALUE_MONTH_NAME = "field_tdr_date_value_month"
BASE_NOMINAL_XML_URL = f"{TREASURY_RATE_XML_URL}?{DATA_NAME}={NOMINAL_DATA_VALUE}"
BASE_REAL_XML_URL = f"{TREASURY_RATE_XML_URL}?{DATA_NAME}={REAL_DATA_VALUE}"


def find_all_ending_with(e: Element, tag: str) -> list[Element]:
    """
    Return all child Elements of 'e' that have a tag that ends with 'tag'.
    """
    return [child for child in e if child.tag.endswith(tag)]


def find_only_one_ending_with(e: Element, tag: str) -> Element:
    """
    Version of find_all_ending_with() that asserts there is only one matching element.
    """
    child_elts = find_all_ending_with(e, tag)
    assert len(child_elts) == 1
    return child_elts[0]


def get_last_entry(root: Element) -> Element:
    """
    Return the last 'entry' Element residing under specified Element.
    """
    last_entry: Element
    entries = find_all_ending_with(root, "entry")
    for elt in entries:
        last_entry = elt

    return last_entry


def extract_stripped_text(e: Element) -> str:
    """Return stripped text value of specifed Element"""
    return e.text.strip()


def extract_decimal(e: Element) -> Decimal:
    """Return Decimal value from text of specifed Element"""
    return Decimal(extract_stripped_text(e))


def extract_rates_from_properties(properties: Element, rates_type: RatesType) -> Rates:
    """
    Given a "properties" element from the Treasury Department XML document,
    return a corresponding Rates object.
    """
    date: str = ""
    r5y: Decimal = None
    r10y: Decimal
    r20y: Decimal
    r30y: Decimal

    for child in properties:
        child_tag = child.tag

        if child_tag.endswith("DATE"):
            date = extract_stripped_text(child)
        elif child_tag.endswith("5YEAR"):
            r5y = extract_decimal(child)
        elif child_tag.endswith("10YEAR"):
            r10y = extract_decimal(child)
        elif child_tag.endswith("20YEAR"):
            r20y = extract_decimal(child)
        elif child_tag.endswith("30YEAR"):
            r30y = extract_decimal(child)

    return Rates(rates_type, date, r5y, r10y, r20y, r30y)


def get_rates(url: str, rt: RatesType) -> Rates:
    """
    Get the XML document at the specified URL, and use its
    contents to build a Rates that is returned.
    """
    page = requests.get(url, timeout=60)
    root = ET.fromstring(page.content)

    # <root>[last]/content/properties
    last_elt = get_last_entry(root)
    content = find_only_one_ending_with(last_elt, "content")
    properties = find_only_one_ending_with(content, "properties")

    return extract_rates_from_properties(properties, rt)


def main() -> None:
    """Simple main()"""

    # I think this should be good enough
    decimal.getcontext().prec = 6

    # build URLS
    today = datetime.date.today()
    date_value_month = today.strftime("%Y%m")
    nominal_url = f"{BASE_NOMINAL_XML_URL}&{DATE_VALUE_MONTH_NAME}={date_value_month}"
    real_url = f"{BASE_REAL_XML_URL}&{DATE_VALUE_MONTH_NAME}={date_value_month}"

    # build our Rates…
    nominal_rates = get_rates(nominal_url, RatesType.NOMINAL)
    real_rates = get_rates(real_url, RatesType.REAL)

    # …and print them out
    nominal_rates.print_as_csv()
    real_rates.print_as_csv()


if __name__ == "__main__":
    main()
