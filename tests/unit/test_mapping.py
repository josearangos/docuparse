from docuparse.engine.paddle_vl import map_page, parse_table

HTML = (
    "<table><tr><td rowspan=\"2\">Concepto</td><td colspan=\"2\">Valor</td></tr>"
    "<tr><td>A</td><td>B</td></tr></table>"
)


def test_html_table_to_grid():
    rows = parse_table(HTML)
    assert [[c.text for c in r] for r in rows] == [["Concepto", "Valor"], ["A", "B"]]
    assert rows[0][0].row_span == 2 and rows[0][1].col_span == 2
    assert rows[1][0].row_span == 1 and rows[1][0].col_span == 1


def test_map_page_types_and_no_html():
    native = {
        "width": 800,
        "height": 1000,
        "parsing_res_list": [
            {"block_label": "text", "block_content": "Hola ñ", "block_bbox": [1, 2, 3, 4]},
            {"block_label": "table", "block_content": HTML, "block_bbox": [1, 2, 3, 4]},
            {"block_label": "display_formula", "block_content": "x^2", "block_bbox": [1, 2, 3, 4]},
            {"block_label": "chart", "block_content": "", "block_bbox": [1, 2, 3, 4]},
        ],
    }
    page = map_page(1, native)
    assert [e.type for e in page.elements] == ["text", "table", "formula", "chart"]
    assert [e.reading_order for e in page.elements] == [1, 2, 3, 4]
    assert page.tables[0].rows[1][1].text == "B"
    assert "<td" not in (page.tables[0].text or "")
    assert page.width == 800
