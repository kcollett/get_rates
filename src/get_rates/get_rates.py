#! /usr/bin/env python3
#
#  -*- mode: python; -*-
#
"""
Script to snarf nominal and real rates from the Treasury Department site
and output in CSV format.
"""
import datetime
import logging
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


@dataclass
class Rates:
    """Class representing a particular set of treasury yields."""

    rt: RatesType
    date: str
    r5y: Decimal
    r10y: Decimal
    r20y: Decimal
    r30y: Decimal

    def __init__(self, properties: Element, rt: RatesType):
        """
        Given a "properties" element from the Treasury Department XML document,
        return a corresponding Rates object.
        """
        self.rt = rt

        for child in properties:
            child_tag = child.tag

            if child_tag.endswith("DATE"):
                self.date = extract_stripped_text(child)
            elif child_tag.endswith("5YEAR"):
                self.r5y = extract_decimal(child)
            elif child_tag.endswith("10YEAR"):
                self.r10y = extract_decimal(child)
            elif child_tag.endswith("20YEAR"):
                self.r20y = extract_decimal(child)
            elif child_tag.endswith("30YEAR"):
                self.r30y = extract_decimal(child)

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


def get_last_entry(root: Element) -> Element | None:
    """
    Return the last 'entry' Element residing under specified Element.
    """
    last_entry: Element
    found_entry = False

    entries = find_all_ending_with(root, "entry")
    logging.debug("number of entries=%d", len(entries))
    for elt in entries:
        last_entry = elt
        found_entry = True

    if found_entry:
        return last_entry
    else:
        return None


def extract_stripped_text(e: Element) -> str:
    """Return stripped text value of specifed Element"""
    if e is None:
        return ""

    etext = e.text
    if etext is None:
        return ""

    return etext.strip()


def extract_decimal(e: Element) -> Decimal:
    """Return Decimal value from text of specifed Element"""
    return Decimal(extract_stripped_text(e))


def get_rates(url: str, rt: RatesType) -> Rates | None:
    """
    Get the XML document at the specified URL, and use its
    contents to build a Rates that is returned.
    """
    response = requests.get(url, timeout=60)
    logging.debug("status=%d", response.status_code)
    root = ET.fromstring(response.content)

    # <root>/entry[last]/content/properties
    last_elt = get_last_entry(root)
    logging.debug("last_elt=%s", str(last_elt))
    if last_elt is None:
        return None
    content = find_only_one_ending_with(last_elt, "content")
    properties = find_only_one_ending_with(content, "properties")

    return Rates(properties, rt)


def main() -> None:
    """Simple main()"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    # I think this should be good enough
    decimal.getcontext().prec = 6

    # build URLS
    today = datetime.date.today()
    date_value_month = today.strftime("%Y%m")
    nominal_url = f"{BASE_NOMINAL_XML_URL}&{DATE_VALUE_MONTH_NAME}={date_value_month}"
    real_url = f"{BASE_REAL_XML_URL}&{DATE_VALUE_MONTH_NAME}={date_value_month}"
    logging.debug("nominal_url=%s", nominal_url)
    logging.debug("real_url=%s", real_url)

    # build our Rates…
    nominal_rates = get_rates(nominal_url, RatesType.NOMINAL)
    real_rates = get_rates(real_url, RatesType.REAL)

    # …and print them out
    if nominal_rates is not None:
        nominal_rates.print_as_csv()
    if real_rates is not None:
        real_rates.print_as_csv()


if __name__ == "__main__":
    main()
