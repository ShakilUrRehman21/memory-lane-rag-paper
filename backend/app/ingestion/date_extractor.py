import re
from datetime import datetime, date
from typing import Optional, Tuple, Dict, Any, List
from app.models.schemas import DateGranularity, DateSource

MONTHS_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12
}

SEASON_BOUNDS = {
    "spring": ("-03-01", "-05-31"),
    "summer": ("-06-01", "-08-31"),
    "fall": ("-09-01", "-11-30"),
    "autumn": ("-09-01", "-11-30"),
    "winter": ("-12-01", "-02-28")
}

QUARTER_BOUNDS = {
    "q1": ("-01-01", "-03-31"),
    "q2": ("-04-01", "-06-30"),
    "q3": ("-07-01", "-09-30"),
    "q4": ("-10-01", "-12-31")
}

class DateExtractor:
    """Disambiguates and extracts Document Date (t_doc) and Event Dates (t_event)."""

    @staticmethod
    def infer_document_date(filename: str, text: str, metadata: Dict[str, Any]) -> Tuple[Optional[str], float]:
        """Detects the authoring/document date t_doc from metadata, headers, or filename."""
        # 1. Check explicit metadata
        for key in ["date", "document_date", "creation_date", "created"]:
            if key in metadata and metadata[key]:
                raw = str(metadata[key]).strip()
                parsed = DateExtractor._parse_iso_or_common(raw)
                if parsed:
                    return parsed, 0.95

        # 2. Check filename (e.g. 2023-05-10_note.md, journal_2022.txt, resume_v2_2024.docx)
        fname_match = re.search(r"\b(20\d{2})[-_](\d{2})[-_](\d{2})\b", filename)
        if fname_match:
            y, m, d = fname_match.groups()
            return f"{y}-{m}-{d}", 0.90
        
        fname_year_match = re.search(r"\b(20\d{2})\b", filename)
        if fname_year_match:
            year = fname_year_match.group(1)
            return f"{year}-01-01", 0.75

        # 3. Check first 15 lines of text for date stamps
        first_lines = "\n".join(text.splitlines()[:15])
        header_date_match = re.search(
            r"(?:date|entry|written|logged|updated)[:\s]+([A-Za-z0-9,\s-]+)",
            first_lines,
            re.IGNORECASE
        )
        if header_date_match:
            cand = header_date_match.group(1).strip()
            parsed = DateExtractor._parse_iso_or_common(cand)
            if parsed:
                return parsed, 0.85

        # 4. Check for standalone date on leading lines
        for line in text.splitlines()[:5]:
            line_str = line.strip("# \t-*")
            parsed = DateExtractor._parse_iso_or_common(line_str)
            if parsed:
                return parsed, 0.80

        return None, 0.0

    @staticmethod
    def extract_event_date(
        statement: str,
        document_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Disambiguates event date t_event from statement text.
        Distinguishes explicit dates vs relative references resolved against t_doc.
        """
        text = statement.strip()
        doc_dt = None
        if document_date:
            try:
                doc_dt = datetime.fromisoformat(document_date.split("T")[0])
            except Exception:
                pass

        # 1. Exact ISO: YYYY-MM-DD
        iso_match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text)
        if iso_match:
            y, m, d = iso_match.groups()
            dt_str = f"{y}-{m}-{d}"
            return {
                "start": dt_str,
                "end": dt_str,
                "granularity": DateGranularity.DAY,
                "confidence": 0.95,
                "source": DateSource.EXPLICIT_IN_TEXT
            }

        # 2. Month Year: e.g. "March 2023", "in Oct 2024"
        month_pattern = r"\b(" + "|".join(MONTHS_MAP.keys()) + r")\.?\s+(20\d{2})\b"
        month_match = re.search(month_pattern, text, re.IGNORECASE)
        if month_match:
            m_str, y_str = month_match.groups()
            m_num = MONTHS_MAP[m_str.lower()]
            start_dt = f"{y_str}-{m_num:02d}-01"
            # calculate end of month
            end_day = 30 if m_num in [4, 6, 9, 11] else (28 if m_num == 2 else 31)
            end_dt = f"{y_str}-{m_num:02d}-{end_day:02d}"
            return {
                "start": start_dt,
                "end": end_dt,
                "granularity": DateGranularity.MONTH,
                "confidence": 0.90,
                "source": DateSource.EXPLICIT_IN_TEXT
            }

        # 3. Season: e.g. "Summer 2023", "Spring 2024"
        season_match = re.search(r"\b(spring|summer|fall|autumn|winter)\s+(20\d{2})\b", text, re.IGNORECASE)
        if season_match:
            season, year = season_match.groups()
            bounds = SEASON_BOUNDS[season.lower()]
            return {
                "start": f"{year}{bounds[0]}",
                "end": f"{year}{bounds[1]}",
                "granularity": DateGranularity.SEASON,
                "confidence": 0.85,
                "source": DateSource.EXPLICIT_IN_TEXT
            }

        # 4. Quarter: e.g. "Q3 2024"
        quarter_match = re.search(r"\b(q[1-4])\s+(20\d{2})\b", text, re.IGNORECASE)
        if quarter_match:
            quarter, year = quarter_match.groups()
            bounds = QUARTER_BOUNDS[quarter.lower()]
            return {
                "start": f"{year}{bounds[0]}",
                "end": f"{year}{bounds[1]}",
                "granularity": DateGranularity.SEASON,
                "confidence": 0.85,
                "source": DateSource.EXPLICIT_IN_TEXT
            }

        # 5. Explicit Year: e.g. "In 2022", "by 2025", "throughout 2024"
        year_match = re.search(r"\b(?:in|during|by|since|around|for|throughout)?\s*(20\d{2})\b", text, re.IGNORECASE)
        if year_match:
            year = year_match.group(1)
            return {
                "start": f"{year}-01-01",
                "end": f"{year}-12-31",
                "granularity": DateGranularity.YEAR,
                "confidence": 0.80,
                "source": DateSource.EXPLICIT_IN_TEXT
            }

        # 6. Relative Temporal Markers resolved against t_doc
        if doc_dt:
            # "last year"
            if re.search(r"\blast year\b", text, re.IGNORECASE):
                target_year = doc_dt.year - 1
                return {
                    "start": f"{target_year}-01-01",
                    "end": f"{target_year}-12-31",
                    "granularity": DateGranularity.YEAR,
                    "confidence": 0.75,
                    "source": DateSource.RELATIVE_INFERRED
                }
            # "two years ago", "3 years ago"
            ago_match = re.search(r"\b(\d+|two|three|four)\s+years?\s+ago\b", text, re.IGNORECASE)
            if ago_match:
                num_map = {"two": 2, "three": 3, "four": 4}
                raw_n = ago_match.group(1).lower()
                n = num_map.get(raw_n, int(raw_n) if raw_n.isdigit() else 1)
                target_year = doc_dt.year - n
                return {
                    "start": f"{target_year}-01-01",
                    "end": f"{target_year}-12-31",
                    "granularity": DateGranularity.YEAR,
                    "confidence": 0.70,
                    "source": DateSource.RELATIVE_INFERRED
                }
            # "earlier this year"
            if re.search(r"\bearlier this year\b", text, re.IGNORECASE):
                return {
                    "start": f"{doc_dt.year}-01-01",
                    "end": doc_dt.strftime("%Y-%m-%d"),
                    "granularity": DateGranularity.SEASON,
                    "confidence": 0.70,
                    "source": DateSource.RELATIVE_INFERRED
                }

        # 7. Fallback to document date if available
        if document_date:
            return {
                "start": document_date,
                "end": document_date,
                "granularity": DateGranularity.DAY if len(document_date) >= 10 else DateGranularity.YEAR,
                "confidence": 0.60,
                "source": DateSource.DOC_METADATA
            }

        # 8. Unrecorded
        return {
            "start": None,
            "end": None,
            "granularity": DateGranularity.UNRECORDED,
            "confidence": 0.0,
            "source": DateSource.DOC_METADATA
        }

    @staticmethod
    def _parse_iso_or_common(text: str) -> Optional[str]:
        text = text.strip().rstrip(".,")
        # Direct YYYY-MM-DD
        m = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text)
        if m:
            y, mo, d = m.groups()
            return f"{y}-{int(mo):02d}-{int(d):02d}"
        
        # Month Day, Year e.g. October 15, 2023
        for mname, mnum in MONTHS_MAP.items():
            if mname in text.lower():
                m_full = re.search(rf"\b{mname}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(20\d{{2}})\b", text, re.IGNORECASE)
                if m_full:
                    d, y = m_full.groups()
                    return f"{y}-{mnum:02d}-{int(d):02d}"
                # Month Year e.g. October 2023
                m_my = re.search(rf"\b{mname}\.?\s+(20\d{{2}})\b", text, re.IGNORECASE)
                if m_my:
                    y = m_my.group(1)
                    return f"{y}-{mnum:02d}-01"

        # Standalone year
        y_match = re.search(r"\b(20\d{2})\b", text)
        if y_match:
            return f"{y_match.group(1)}-01-01"

        return None
