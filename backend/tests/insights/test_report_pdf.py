from investment_agent.insights.pdf import extract_pages


def tiny_pdf(texts):
    """A minimal hand-written PDF with one Helvetica text line per page."""
    objs, kids = [b"<< /Type /Catalog /Pages 2 0 R >>", None, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"], []
    for t in texts:
        stream = f"BT /F1 12 Tf 72 720 Td ({t}) Tj ET".encode()
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        content_id = len(objs)
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> "
                    f"/Contents {content_id} 0 R >>".encode())
        kids.append(len(objs))
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>".encode()
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


def test_pages_are_extracted_in_order_and_capped():
    pages = extract_pages(tiny_pdf(["GDP growth 7.5 percent", "Banks benefit from rates", "third"]), max_pages=2)
    assert len(pages) == 2 and "GDP growth 7.5 percent" in pages[0] and "Banks benefit" in pages[1]


def test_unreadable_bytes_give_no_pages():
    assert extract_pages(b"not a pdf") == []
