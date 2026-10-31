import io
import json
import zipfile
from datetime import datetime, timezone

from investment_agent.market.erp import ErpStore, erp_sync, parse_country_erp

M = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _xlsx(rows: list[list]) -> bytes:
    """A two-sheet workbook shaped like Damodaran's ctryprem.xlsx (shared strings, numbers as values)."""
    strings: list[str] = []

    def cell(ref, v):
        if isinstance(v, str):
            strings.append(v)
            return f'<c r="{ref}" t="s"><v>{len(strings) - 1}</v></c>'
        return f'<c r="{ref}"><v>{v}</v></c>'
    body = "".join(f'<row r="{i + 1}">' + "".join(cell(f"{chr(65 + j)}{i + 1}", v) for j, v in enumerate(r) if v is not None) + "</row>"
                   for i, r in enumerate(rows))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook xmlns="{M}" xmlns:r="{R}"><sheets><sheet name="Explanation and FAQ" sheetId="1" r:id="rId1"/>'
                                      f'<sheet name="ERPs by country" sheetId="2" r:id="rId2"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{M}"><sheetData/></worksheet>')
        z.writestr("xl/worksheets/sheet2.xml", f'<worksheet xmlns="{M}"><sheetData>{body}</sheetData></worksheet>')
        z.writestr("xl/sharedStrings.xml", f'<sst xmlns="{M}">' + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>")
    return buf.getvalue()


BOOK = _xlsx([["Country and Equity Risk Premiums"], [],
              ["Country", "Africa", "Moody's rating", "Rating-based Default Spread", "Total Equity Risk Premium", "Country Risk Premium",
               "Sovereign CDS, net of Swiss CDS", "Total Equity Risk Premium2"],
              ["Thailand", "Asia", "Baa1", 0.0151, 0.0653, 0.023, 0.0066, 0.0523],
              ["Vietnam", "Asia", "Ba2", 0.025569819499326372, 0.081252503854626124, 0.038952503854626126, 0.0137, 0.063170280403130594]])


def test_vietnam_row_is_read_by_header_names_not_cell_positions():
    assert parse_country_erp(BOOK, "Vietnam") == {"erp": "0.0813", "erp_cds": "0.0632", "rating": "Ba2"}
    assert parse_country_erp(BOOK, "Atlantis") is None


def test_sync_stores_the_premium_with_the_file_date_and_waits_a_week_before_reading_again(tmp_path):
    calls = []

    def get(url):
        calls.append(url)
        return BOOK, "Mon, 16 Feb 2026 22:20:18 GMT"
    now = datetime(2026, 10, 31, tzinfo=timezone.utc)
    assert erp_sync(ErpStore(tmp_path), get=get, now=now)["status"] == "ok"
    saved = ErpStore(tmp_path).read()
    assert saved["erp"] == "0.0813" and saved["published"] == "2026-02-16" and saved["rating"] == "Ba2" and "ctryprem.xlsx" in calls[0]
    assert erp_sync(ErpStore(tmp_path), get=get, now=datetime(2026, 11, 5, tzinfo=timezone.utc))["status"] == "fresh"
    assert len(calls) == 1


def test_a_book_without_vietnam_keeps_the_old_value(tmp_path):
    store = ErpStore(tmp_path)
    store.save({"erp": "0.0813", "published": "2026-02-16", "fetched_at": "2026-01-01T00:00:00+00:00"})
    out = erp_sync(store, get=lambda url: (_xlsx([["Country", "Total Equity Risk Premium"]]), None), now=datetime(2026, 10, 31, tzinfo=timezone.utc))
    assert out["status"] == "error" and json.loads(store.path.read_text(encoding="utf-8"))["erp"] == "0.0813"


def test_cli_erp_sync_prints_the_outcome(tmp_path, capsys):
    from investment_agent.cli import erp_sync_cli
    assert erp_sync_cli(tmp_path, get=lambda url: (BOOK, "Mon, 16 Feb 2026 22:20:18 GMT")) == 0
    assert json.loads(capsys.readouterr().out) == {"status": "ok", "erp": "0.0813", "published": "2026-02-16"}
    assert erp_sync_cli(tmp_path / "x", get=lambda url: (_xlsx([]), None)) == 1
