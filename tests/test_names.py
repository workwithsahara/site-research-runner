import names


def test_junk_first_names_are_blank():
    for junk in ["Past", "Can Trust", "Sourcing City", "Wedding Planner", "Hours Council", "Veterinary Surgeon",
                 "Certified Arborist", "Practice", "Brow Artist", "Raleigh Region", "Lisa Studio", "Golden Holt",
                 "Happy Property", "Dr Ereeny", "Staff Station", ""]:
        assert names.first_name(junk) == "", junk


def test_real_names_are_kept():
    assert names.first_name("Pamela Hill") == "Pamela"
    assert names.first_name("Rewi Erickson") == "Rewi"
    assert names.first_name("Kathy Glass") == "Kathy"
    assert names.first_name("Christine") == "Christine"
