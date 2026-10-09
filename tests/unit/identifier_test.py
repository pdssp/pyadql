"""Tests for the Identifier class and its comparison/hashing behavior."""

import pytest

from pyadql import ast_nodes as A


class TestIdentifierCreation:
    """Test Identifier creation via from_string()."""

    def test_from_string_undelimited_normalized(self):
        """Undelimited identifiers should be normalized to lowercase."""
        id1 = A.Identifier.from_string("MyTable")
        assert id1.name == "mytable"
        assert id1.is_delimited is False

    def test_from_string_undelimited_uppercase(self):
        """Uppercase undelimited identifiers should be normalized."""
        id1 = A.Identifier.from_string("MYTABLE")
        assert id1.name == "mytable"
        assert id1.is_delimited is False

    def test_from_string_delimited_preserves_case(self):
        """Delimited identifiers should preserve casing."""
        id1 = A.Identifier.from_string('"MyTable"')
        assert id1.name == "MyTable"
        assert id1.is_delimited is True

    def test_from_string_delimited_unescape_quotes(self):
        """Delimited identifiers should unescape doubled quotes."""
        id1 = A.Identifier.from_string('"Table""X"')
        assert id1.name == 'Table"X'
        assert id1.is_delimited is True


class TestIdentifierMatches:
    """Test the matches() method with SQL case-sensitivity semantics."""

    # String matching tests
    def test_matches_undelimited_string_case_insensitive(self):
        """Undelimited identifier matches string case-insensitively."""
        id1 = A.Identifier.from_string("ra")
        assert id1.matches("ra")
        assert id1.matches("RA")
        assert id1.matches("Ra")

    def test_matches_delimited_string_case_sensitive(self):
        """Delimited identifier matches string case-sensitively."""
        id1 = A.Identifier.from_string('"MyCol"')
        assert id1.matches("MyCol")
        assert not id1.matches("mycol")
        assert not id1.matches("MYCOL")

    def test_matches_delimited_string_exact_match(self):
        """Delimited identifier requires exact case match with string."""
        id1 = A.Identifier.from_string('"MyCol"')
        assert id1.matches("MyCol")
        assert not id1.matches("MyCol ")  # extra space
        assert not id1.matches(" MyCol")  # leading space

    # Identifier matching tests (case-insensitive if either undelimited)
    def test_matches_undelimited_to_undelimited(self):
        """Two undelimited identifiers match case-insensitively."""
        id1 = A.Identifier.from_string("ra")
        id2 = A.Identifier.from_string("RA")
        assert id1.matches(id2)
        assert id2.matches(id1)

    def test_matches_delimited_to_delimited_same_case(self):
        """Two delimited identifiers match case-sensitively (same case)."""
        id1 = A.Identifier.from_string('"MyCol"')
        id2 = A.Identifier.from_string('"MyCol"')
        assert id1.matches(id2)

    def test_matches_delimited_to_delimited_different_case(self):
        """Two delimited identifiers don't match with different case."""
        id1 = A.Identifier.from_string('"MyCol"')
        id2 = A.Identifier.from_string('"mycol"')
        assert not id1.matches(id2)
        assert not id2.matches(id1)

    def test_matches_undelimited_to_delimited_case_insensitive(self):
        """Undelimited + delimited match case-insensitively."""
        id1 = A.Identifier.from_string("ra")
        id2 = A.Identifier.from_string('"RA"')
        assert id1.matches(id2)
        assert id2.matches(id1)

    def test_matches_undelimited_to_delimited_mixed_case(self):
        """Undelimited + delimited with different cases still match."""
        id1 = A.Identifier.from_string("table")
        id2 = A.Identifier.from_string('"TABLE"')
        id3 = A.Identifier.from_string('"Table"')
        assert id1.matches(id2)
        assert id1.matches(id3)
        assert id2.matches(id1)

    def test_matches_delimited_to_undelimited_case_insensitive(self):
        """Delimited + undelimited match case-insensitively."""
        id1 = A.Identifier.from_string('"MyCol"')
        id2 = A.Identifier.from_string("mycol")
        assert id1.matches(id2)
        assert id2.matches(id1)

    # Different names don't match
    def test_matches_different_names_undelimited(self):
        """Different names should not match (undelimited)."""
        id1 = A.Identifier.from_string("ra")
        id2 = A.Identifier.from_string("dec")
        assert not id1.matches(id2)

    def test_matches_different_names_delimited(self):
        """Different names should not match (delimited)."""
        id1 = A.Identifier.from_string('"Col1"')
        id2 = A.Identifier.from_string('"Col2"')
        assert not id1.matches(id2)

    def test_matches_different_names_mixed(self):
        """Different names should not match (mixed delimiters)."""
        id1 = A.Identifier.from_string("ra")
        id2 = A.Identifier.from_string('"dec"')
        assert not id1.matches(id2)

    # Invalid type handling
    def test_matches_invalid_type_returns_not_implemented(self):
        """matches() with invalid type should return NotImplemented."""
        id1 = A.Identifier.from_string("ra")
        assert id1.matches(42) == NotImplemented
        assert id1.matches(None) == NotImplemented
        assert id1.matches([]) == NotImplemented
