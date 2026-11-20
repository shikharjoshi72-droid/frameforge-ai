from core.schedule_generator import generate_schedule, parse_availability


def scenes(n=12):
    out = []
    for i in range(1, n + 1):
        out.append({"id": i, "seq": float(i), "scene_number": str(i), "location": ["KITCHEN", "PARK", "WAREHOUSE"][i % 3],
                    "int_ext": "INT", "time_of_day": "NIGHT" if i % 4 == 0 else "DAY", "complexity": "Medium",
                    "characters": ["ANNA", "BEN"] if i % 2 else ["CARLA"], "vehicles": [], "special_effects": []})
    return out


def test_deterministic():
    a, b = generate_schedule(scenes(), "2026-12-01"), generate_schedule(scenes(), "2026-12-01")
    assert a == b


def test_every_scene_scheduled_once_and_units_not_mixed():
    sc = scenes()
    r = generate_schedule(sc, capacity=300)
    ids = [i for d in r["days"] for i in d["scene_ids"]]
    assert sorted(ids) == sorted(s["id"] for s in sc)
    by_id = {s["id"]: s for s in sc}
    for d in r["days"]:
        assert len({by_id[i]["time_of_day"] == "NIGHT" for i in d["scene_ids"]}) == 1


def test_capacity_respected_and_dates_skip_weekends():
    r = generate_schedule(scenes(), "2026-12-04", capacity=300)  # Friday
    assert all(d["est_minutes"] <= 300 + 90 for d in r["days"])
    dates = [d["shoot_date"] for d in r["days"]]
    assert dates[0] == "2026-12-04" and dates[1] == "2026-12-07"


def test_no_start_date_means_pending_dates():
    assert all(d["shoot_date"] is None for d in generate_schedule(scenes())["days"])


def test_availability_conflict():
    r = generate_schedule(scenes(), availability=parse_availability("ANNA: day 1"))
    assert any(c["type"] == "availability" and "ANNA" in c["message"] for c in r["conflicts"])
