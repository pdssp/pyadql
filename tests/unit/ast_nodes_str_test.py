"""Tests for AST node string representation methods (__str__) and utilities."""

import pytest

from pyadql import ast_nodes as A


class TestIdentifierStr:
    """Test Identifier.__str__() method"""
    
    def test_str_undelimited_simple(self):
        """Undelimited identifier returns name as-is (lowercase)"""
        ident = A.Identifier.from_string("MyTable")
        assert str(ident) == "mytable"
    
    def test_str_undelimited_already_lower(self):
        """Undelimited identifier already lowercase"""
        ident = A.Identifier.from_string("table")
        assert str(ident) == "table"
    
    def test_str_delimited_simple(self):
        """Delimited identifier wraps in double quotes"""
        ident = A.Identifier.from_string('"MyTable"')
        assert str(ident) == '"MyTable"'
    
    def test_str_delimited_with_internal_quotes(self):
        """Delimited identifier escapes internal quotes by doubling"""
        ident = A.Identifier.from_string('"Table""X"')
        assert str(ident) == '"Table""X"'
    
    def test_str_delimited_with_spaces(self):
        """Delimited identifier preserves spaces"""
        ident = A.Identifier.from_string('"My Table"')
        assert str(ident) == '"My Table"'
    
    def test_str_delimited_with_special_chars(self):
        """Delimited identifier preserves special characters"""
        ident = A.Identifier.from_string('"My-Table@1"')
        assert str(ident) == '"My-Table@1"'


class TestIdentifierJoinQualifiedName:
    """Test Identifier.join_qualified_name() static method"""
    
    def test_join_single_identifier(self):
        """Single identifier returns just that identifier"""
        ident = A.Identifier.from_string("table")
        result = A.Identifier.join_qualified_name([ident])
        assert result == "table"
    
    def test_join_two_undelimited(self):
        """Two undelimited identifiers joined with dot"""
        schema = A.Identifier.from_string("public")
        table = A.Identifier.from_string("users")
        result = A.Identifier.join_qualified_name([schema, table])
        assert result == "public.users"
    
    def test_join_two_delimited(self):
        """Two delimited identifiers joined with dot"""
        schema = A.Identifier.from_string('"MySchema"')
        table = A.Identifier.from_string('"MyTable"')
        result = A.Identifier.join_qualified_name([schema, table])
        assert result == '"MySchema"."MyTable"'
    
    def test_join_mixed_delimiters(self):
        """Mix of delimited and undelimited identifiers"""
        schema = A.Identifier.from_string("public")
        table = A.Identifier.from_string('"User"')
        result = A.Identifier.join_qualified_name([schema, table])
        assert result == 'public."User"'
    
    def test_join_with_escaped_quotes(self):
        """Delimited identifier with escaped quotes in join"""
        schema = A.Identifier.from_string('"Sch""ema"')
        table = A.Identifier.from_string('"Col""Name"')
        result = A.Identifier.join_qualified_name([schema, table])
        assert result == '"Sch""ema"."Col""Name"'
    
    def test_join_three_identifiers(self):
        """Three identifiers (catalog.schema.table)"""
        catalog = A.Identifier.from_string("catalog")
        schema = A.Identifier.from_string("public")
        table = A.Identifier.from_string("users")
        result = A.Identifier.join_qualified_name([catalog, schema, table])
        assert result == "catalog.public.users"


class TestColumnRefStr:
    """Test ColumnRef.__str__() method using join_qualified_name"""
    
    def test_str_simple_column(self):
        """Simple column reference (no qualification)"""
        col = A.Identifier.from_string("id")
        ref = A.ColumnRef(parts=[col])
        assert str(ref) == "id"
    
    def test_str_qualified_column(self):
        """Table-qualified column reference"""
        table = A.Identifier.from_string("t")
        col = A.Identifier.from_string("id")
        ref = A.ColumnRef(parts=[table, col])
        assert str(ref) == "t.id"
    
    def test_str_qualified_delimited(self):
        """Qualified column with delimited identifiers"""
        table = A.Identifier.from_string('"User"')
        col = A.Identifier.from_string('"ID"')
        ref = A.ColumnRef(parts=[table, col])
        assert str(ref) == '"User"."ID"'
    
    def test_str_mixed_qualified(self):
        """Mixed delimited/undelimited qualification"""
        table = A.Identifier.from_string("public")
        col = A.Identifier.from_string('"MyCol"')
        ref = A.ColumnRef(parts=[table, col])
        assert str(ref) == 'public."MyCol"'
    
    def test_str_schema_qualified_column(self):
        """Schema.table.column reference"""
        schema = A.Identifier.from_string("public")
        table = A.Identifier.from_string("users")
        col = A.Identifier.from_string("name")
        ref = A.ColumnRef(parts=[schema, table, col])
        assert str(ref) == "public.users.name"


class TestTableRefStr:
    """Test TableRef.__str__() method"""
    
    def test_str_simple_table(self):
        """Simple table reference without alias"""
        table = A.Identifier.from_string("users")
        ref = A.TableRef(name=[table])
        assert str(ref) == "users"
    
    def test_str_schema_qualified_table(self):
        """Schema-qualified table"""
        schema = A.Identifier.from_string("public")
        table = A.Identifier.from_string("users")
        ref = A.TableRef(name=[schema, table])
        assert str(ref) == "public.users"
    
    def test_str_table_with_alias(self):
        """Table with alias"""
        table = A.Identifier.from_string("users")
        alias = A.Identifier.from_string("u")
        ref = A.TableRef(name=[table], alias=alias)
        assert str(ref) == "users AS u"
    
    def test_str_schema_qualified_with_alias(self):
        """Schema-qualified table with alias"""
        schema = A.Identifier.from_string("public")
        table = A.Identifier.from_string("users")
        alias = A.Identifier.from_string("u")
        ref = A.TableRef(name=[schema, table], alias=alias)
        assert str(ref) == "public.users AS u"
    
    def test_str_table_with_columns(self):
        """Table with column renaming list"""
        table = A.Identifier.from_string("users")
        alias = A.Identifier.from_string("u")
        ref = A.TableRef(name=[table], alias=alias, columns=["id", "name"])
        assert str(ref) == "users AS u (id, name)"
    
    def test_str_table_with_single_column(self):
        """Table with single column in rename list"""
        table = A.Identifier.from_string("t")
        alias = A.Identifier.from_string("x")
        ref = A.TableRef(name=[table], alias=alias, columns=["col1"])
        assert str(ref) == "t AS x (col1)"
    
    def test_str_delimited_table_names(self):
        """Delimited table and schema names"""
        schema = A.Identifier.from_string('"MySchema"')
        table = A.Identifier.from_string('"UserTable"')
        alias = A.Identifier.from_string('u')
        ref = A.TableRef(name=[schema, table], alias=alias)
        assert str(ref) == '"MySchema"."UserTable" AS u'
    
    def test_str_full_reference_delimited_with_columns(self):
        """Complete reference with delimited names and columns"""
        schema = A.Identifier.from_string('"Catalog"')
        table = A.Identifier.from_string('"User"')
        alias = A.Identifier.from_string('"U"')
        ref = A.TableRef(name=[schema, table], alias=alias, columns=["uid", "uname"])
        assert str(ref) == '"Catalog"."User" AS "U" (uid, uname)'
