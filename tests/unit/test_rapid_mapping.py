from docuparse.engine.rapid import map_page


def test_lines_become_ordered_text_elements():
    boxes = [
        [[10, 100], [90, 100], [90, 120], [10, 120]],
        [[10, 10], [200, 10], [200, 30], [10, 30]],
    ]
    page = map_page(1, 300, 200, boxes, ["segunda", "Señor Muñoz"], [0.9, 1.5])
    assert [e.text for e in page.elements] == ["Señor Muñoz", "segunda"]
    assert [e.reading_order for e in page.elements] == [1, 2]
    assert page.elements[0].confidence == 1.0  # clamped to the schema range
    assert page.elements[0].bbox.right == 200
    assert page.tables == []
