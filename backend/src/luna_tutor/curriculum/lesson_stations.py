"""Station boundaries for the authored Grade 3 Unit 1 lessons.

Orders are one-based item positions in each lesson's ``content.yaml``.
The lesson authoring contract keeps these progression rules in code.
"""

from typing import Literal

StationId = Literal[1, 2, 3]

# Each tuple contains the first item order for stations 1, 2, and 3.
_STATION_START_ORDERS: dict[int, tuple[int, int, int]] = {
    1: (7, 15, 22),
    2: (1, 9, 18),
    3: (1, 9, 17),
    4: (1, 10, 15),
}


def active_station(lesson_id: int, item_index: int) -> StationId | None:
    """Return the station containing the current zero-based lesson item."""
    start_orders = _STATION_START_ORDERS.get(lesson_id)
    if start_orders is None or item_index < 0:
        return None

    item_order = item_index + 1
    station: StationId | None = None
    for station_id, start_order in enumerate(start_orders, start=1):
        if item_order < start_order:
            break
        station = station_id  # type: ignore[assignment]
    return station
