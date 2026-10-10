import pytest
from pydantic import ValidationError

from app.contracts import SmokeResponse, Taxonomy, TaxonomyEntry, load_taxonomy, require_classification_taxonomy


def seed():
    return Taxonomy(revision="synthetic", source_sha256="0" * 64, entries=[TaxonomyEntry(
        name="Fixture label", family="fixture", definition="Synthetic only", source_url="fixture://test",
        source_row=2, boundary="No official meaning", provenance="synthetic")])


def test_missing_taxonomy_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="TAXONOMY_MISSING"):
        load_taxonomy(tmp_path / "absent.json")
    with pytest.raises(ValueError, match="TAXONOMY_MISSING"):
        require_classification_taxonomy(None)


def test_names_confirmation_does_not_approve_definitions():
    data = seed().model_dump()
    data.update(names_confirmed=True, names_authority="Test reviewer")
    with pytest.raises(ValueError, match="DEFINITIONS_UNAPPROVED"):
        require_classification_taxonomy(Taxonomy.model_validate(data))
    data.update(definitions_approved=True, definitions_authority="Test reviewer")
    require_classification_taxonomy(Taxonomy.model_validate(data))


def test_unconfirmed_names_block():
    with pytest.raises(ValueError, match="NAMES_UNCONFIRMED"):
        require_classification_taxonomy(seed())


def test_duplicate_labels_and_missing_authority_rejected():
    data = seed().model_dump()
    data["entries"] *= 2
    with pytest.raises(ValidationError):
        Taxonomy.model_validate(data)
    data = seed().model_dump()
    data["names_confirmed"] = True
    with pytest.raises(ValidationError):
        Taxonomy.model_validate(data)


def test_unknown_model_fields_and_wrong_values_rejected():
    good = dict(record_id="SYNTHETIC-SMOKE-001", amount="0.00", missing_currency=True)
    SmokeResponse.model_validate(good)
    with pytest.raises(ValidationError):
        SmokeResponse.model_validate({**good, "execute": "untrusted"})
    with pytest.raises(ValidationError):
        SmokeResponse.model_validate({**good, "amount": "42"})
