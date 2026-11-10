"""A small synthetic workbook laid out like the owner's monthly spending file: a 'Tổng' sheet with a header row of labelled columns and one row per
month. Figures are made up. Used by the backend tests and to write the browser test's fixture."""

import io
import zipfile
from xml.sax.saxutils import escape

GROUPS = {"H": "LỢI NHUẬN TỪ  KINH DOANH", "M": "LỢI NHUẬN TỪ DANH MỤC ĐẦU TƯ"}
HEADERS = {"C": "Tháng", "D": "Tổng Thu nhập kinh doanh", "E": "Tổng Chi", "F": "Tổng\nTiết kiệm được", "G": "% \ntiết kiệm được", "H": "CA HĐĐT BHXH",
           "I": "Căn hộ cho thuê", "L": "Youtube, Tiktok, Affiliate", "M": "Tiền gửi", "O": "Trái phiếu", "P": "Cổ phiếu"}
SOURCES = {"I": 20_000_000, "M": 2_000_000, "O": 1_000_000, "H": 30_000_000, "L": 500_000, "P": 3_000_000}


def month_rows(months=range(1, 11), income=60_000_000, spending=40_000_000):
    return {m: {"D": income + m * 1_000_000, "E": spending + m * 500_000, **SOURCES} for m in months}


def workbook(rows: dict[int, dict[str, int | None]] | None = None, *, year=2026, uncached=(), extra_sheets=("Tháng 1",), total_name="Tổng") -> bytes:
    """rows: month -> {column: amount}; uncached: (month, column) written as a formula with no cached value."""
    rows = month_rows() if rows is None else rows
    strings: list[str] = []

    def s(text):
        if text not in strings:
            strings.append(text)
        return strings.index(text)

    def cell(ref, value=None, *, text=None, formula=None):
        if text is not None:
            return f'<c r="{ref}" t="s"><v>{s(text)}</v></c>'
        f = f"<f>{escape(formula)}</f>" if formula else ""
        return f'<c r="{ref}">{f}{"" if value is None else f"<v>{value}</v>"}</c>'

    xml_rows = [f'<row r="3">{cell("C3", text="Năm hiện tại")}{cell("D3", year)}' + "".join(cell(f"{c}3", text=t) for c, t in GROUPS.items()) + "</row>",
                '<row r="4">' + "".join(cell(f"{c}4", text=t) for c, t in HEADERS.items()) + "</row>"]
    for i, (m, values) in enumerate(sorted(rows.items())):
        r = 5 + i
        cells = [cell(f"C{r}", m)]
        for col, v in values.items():
            if (m, col) in uncached:
                cells.append(cell(f"{col}{r}", formula=f"'Tháng {m}'!H1"))
            elif v is not None:
                cells.append(cell(f"{col}{r}", v, formula=f"'Tháng {m}'!E5"))
        xml_rows.append(f'<row r="{r}">' + "".join(cells) + "</row>")
    sheet = ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
             + "".join(xml_rows) + "</sheetData></worksheet>")
    empty = '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>'
    names = [*extra_sheets, total_name]
    workbook_xml = ('<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                    + "".join(f'<sheet name="{escape(n)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, n in enumerate(names)) + "</sheets></workbook>")
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
                      for i in range(len(names))) + "</Relationships>")
    shared = ('<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
              + "".join(f"<si><t>{escape(t)}</t></si>" for t in strings) + "</sst>")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/sharedStrings.xml", shared)
        for i, n in enumerate(names):
            z.writestr(f"xl/worksheets/sheet{i + 1}.xml", sheet if n == total_name else empty)
    return out.getvalue()


if __name__ == "__main__":
    import sys
    open(sys.argv[1], "wb").write(workbook())
