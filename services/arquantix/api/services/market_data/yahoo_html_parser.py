"""
Yahoo Finance HTML table parser
Parses HTML table from Yahoo Finance "Historical Data" page
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
from bs4 import BeautifulSoup
import re


class ParsedBar:
    """A parsed OHLCV bar"""
    def __init__(self, date: date, open: Decimal, high: Decimal, low: Decimal, close: Decimal, volume: int):
        self.date = date
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


class ParsedEvent:
    """A parsed corporate action event (dividend, split)"""
    def __init__(self, date: date, event_type: str, value: str):
        self.date = date
        self.event_type = event_type  # "dividend" or "split"
        self.value = value  # e.g., "0.01" for dividend, "2:1" for split


class SkippedRow:
    """A row that was skipped during parsing"""
    def __init__(self, row_index: int, raw: str, reason: str):
        self.row_index = row_index
        self.raw = raw
        self.reason = reason


def parse_date(date_str: str) -> Optional[date]:
    """
    Parse date string from Yahoo Finance format
    Supports: "Jan 8, 2026", "2026-01-08", "Jan 08, 2026"
    """
    date_str = date_str.strip()
    
    # Try ISO format first
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        pass
    
    # Try Yahoo format: "Jan 8, 2026" or "Jan 08, 2026"
    formats = [
        "%b %d, %Y",  # Jan 8, 2026
        "%B %d, %Y",  # January 8, 2026
        "%b %d %Y",   # Jan 8 2026 (no comma)
        "%B %d %Y",   # January 8 2026 (no comma)
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None


def parse_decimal(value_str: str) -> Optional[Decimal]:
    """Parse decimal value, handling commas and dashes"""
    if not value_str:
        return None
    
    value_str = value_str.strip().replace(',', '')
    
    if value_str == '-' or value_str == '' or value_str.lower() == 'null':
        return None
    
    try:
        return Decimal(value_str)
    except (ValueError, TypeError):
        return None


def parse_volume(volume_str: str) -> Optional[int]:
    """Parse volume as integer, handling commas"""
    if not volume_str:
        return None
    
    volume_str = volume_str.strip().replace(',', '')
    
    if volume_str == '-' or volume_str == '' or volume_str.lower() == 'null':
        return None
    
    try:
        return int(volume_str)
    except (ValueError, TypeError):
        return None


def parse_event_row(row, row_index: int) -> Optional[ParsedEvent]:
    """
    Parse a corporate action event row (dividend, split)
    Format: <td>Dec 4, 2025</td><td colspan="6">0.01 Dividend</td>
    """
    tds = row.find_all('td')
    if len(tds) < 2:
        return None
    
    # Check if second td has colspan (event row indicator)
    second_td = tds[1]
    if not second_td.get('colspan'):
        return None
    
    # Parse date from first td
    date_str = tds[0].get_text(strip=True)
    event_date = parse_date(date_str)
    if not event_date:
        return None
    
    # Parse event from second td
    event_text = second_td.get_text(strip=True)
    
    # Try to detect dividend: "0.01 Dividend" or "Dividend 0.01"
    dividend_match = re.search(r'([\d.]+)\s*Dividend', event_text, re.IGNORECASE)
    if dividend_match:
        return ParsedEvent(event_date, "dividend", dividend_match.group(1))
    
    # Try to detect split: "2:1 Split" or "Split 2:1"
    split_match = re.search(r'(\d+:\d+)\s*Split', event_text, re.IGNORECASE)
    if split_match:
        return ParsedEvent(event_date, "split", split_match.group(1))
    
    # Generic event (unknown type)
    return ParsedEvent(event_date, "unknown", event_text)


def parse_ohlcv_row(row, row_index: int) -> Optional[ParsedBar]:
    """
    Parse a standard OHLCV row
    Expected columns: Date, Open, High, Low, Close, Adj Close, Volume
    """
    tds = row.find_all('td')
    
    # Expect 7 columns
    if len(tds) < 7:
        return None
    
    # Extract text from each column
    date_str = tds[0].get_text(strip=True)
    open_str = tds[1].get_text(strip=True)
    high_str = tds[2].get_text(strip=True)
    low_str = tds[3].get_text(strip=True)
    close_str = tds[4].get_text(strip=True)
    adj_close_str = tds[5].get_text(strip=True)  # Not used for now
    volume_str = tds[6].get_text(strip=True)
    
    # Parse date
    bar_date = parse_date(date_str)
    if not bar_date:
        return None
    
    # Parse numeric values
    open_price = parse_decimal(open_str)
    high_price = parse_decimal(high_str)
    low_price = parse_decimal(low_str)
    close_price = parse_decimal(close_str)
    volume = parse_volume(volume_str)
    
    # Validate required fields
    if open_price is None or close_price is None:
        return None
    
    # Use close as fallback for high/low if missing
    if high_price is None:
        high_price = close_price
    if low_price is None:
        low_price = close_price
    
    # Volume can be 0 but should be present
    if volume is None:
        volume = 0
    
    return ParsedBar(
        date=bar_date,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume
    )


def parse_yahoo_html_table(html: str) -> Tuple[List[ParsedBar], List[ParsedEvent], List[SkippedRow]]:
    """
    Parse Yahoo Finance HTML table
    
    Args:
        html: Raw HTML string containing a <table> element
        
    Returns:
        Tuple of (bars, events, skipped_rows)
    """
    bars: List[ParsedBar] = []
    events: List[ParsedEvent] = []
    skipped_rows: List[SkippedRow] = []
    
    # Parse HTML
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find first table
    table = soup.find('table')
    if not table:
        raise ValueError("No <table> element found in HTML")
    
    # Find tbody (or use table directly if no tbody)
    tbody = table.find('tbody')
    if not tbody:
        tbody = table
    
    # Iterate rows
    rows = tbody.find_all('tr')
    if not rows:
        raise ValueError("No <tr> rows found in table")
    
    for row_index, row in enumerate(rows):
        row_text = row.get_text(strip=True)
        
        # Skip empty rows
        if not row_text:
            continue
        
        # Check if this is an event row (dividend/split)
        tds = row.find_all('td')
        if len(tds) >= 2 and tds[1].get('colspan'):
            # This is an event row
            event = parse_event_row(row, row_index)
            if event:
                events.append(event)
            else:
                skipped_rows.append(SkippedRow(
                    row_index=row_index,
                    raw=row_text,
                    reason="Event row format not recognized"
                ))
            continue
        
        # Try to parse as OHLCV row
        bar = parse_ohlcv_row(row, row_index)
        if bar:
            bars.append(bar)
        else:
            skipped_rows.append(SkippedRow(
                row_index=row_index,
                raw=row_text,
                reason="Could not parse as OHLCV row (missing date or prices)"
            ))
    
    return bars, events, skipped_rows

