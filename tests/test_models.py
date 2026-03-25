from gedinfo.models import Individual, Family, GedcomData


def test_individual_defaults():
    indi = Individual(id="@I001@")
    assert indi.id == "@I001@"
    assert indi.first_name is None
    assert indi.last_name is None
    assert indi.sex == "U"
    assert indi.family_ids_as_child == []
    assert indi.family_ids_as_spouse == []


def test_individual_specified():
    indi = Individual(
        id="@I002@",
        first_name="Alice",
        last_name="Smith",
        sex="F",
        family_ids_as_child=["@F001@"],
        family_ids_as_spouse=["@F002@"],
    )
    assert indi.id == "@I002@"
    assert indi.first_name == "Alice"
    assert indi.last_name == "Smith"
    assert indi.sex == "F"
    assert indi.family_ids_as_child == ["@F001@"]
    assert indi.family_ids_as_spouse == ["@F002@"]


def test_individual_equality():
    a = Individual(id="@I003@", first_name="Bob")
    b = Individual(id="@I003@", first_name="Bob")
    assert a == b


def test_family_defaults_and_specified():
    fam = Family(id="@F001@")
    assert fam.id == "@F001@"
    assert fam.husband_id is None
    assert fam.wife_id is None
    assert fam.child_ids == []

    fam2 = Family(
        id="@F002@",
        husband_id="@I001@",
        wife_id="@I002@",
        child_ids=["@I003@"],
    )
    assert fam2.id == "@F002@"
    assert fam2.husband_id == "@I001@"
    assert fam2.wife_id == "@I002@"
    assert fam2.child_ids == ["@I003@"]


def test_gedcomdata_container():
    data = GedcomData()
    i = Individual(id="@I001@")
    f = Family(id="@F001@")
    data.individuals[i.id] = i
    data.families[f.id] = f
    assert data.individuals["@I001@"] is i
    assert data.families["@F001@"] is f


def test_mutable_defaults_not_shared():
    a = Individual(id="@I004@")
    b = Individual(id="@I005@")
    a.family_ids_as_child.append("@F000@")
    assert b.family_ids_as_child == []

    x = Family(id="@F003@")
    y = Family(id="@F004@")
    x.child_ids.append("@I000@")
    assert y.child_ids == []


def test_individual_living_default():
    indi = Individual(id="@I001@")
    assert indi.living is None


def test_individual_living_true_false_and_equality():
    a = Individual(id="@I010@", living=True)
    b = Individual(id="@I010@", living=True)
    c = Individual(id="@I010@", living=None)
    assert a == b
    assert a != c
