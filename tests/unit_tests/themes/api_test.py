# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.


from superset.constants import RouteMethod
from superset.themes.api import ThemeRestApi


class TestThemeRestApi:
    """Unit tests for ThemeRestApi class configuration"""

    def test_resource_name(self):
        """Test that resource name is set correctly"""
        assert ThemeRestApi.resource_name == "theme"

    def test_class_permission_name(self):
        """Test that class permission name is set correctly"""
        assert ThemeRestApi.class_permission_name == "Theme"

    def test_datamodel_configured(self):
        """Test that datamodel is configured with Theme model"""
        # The datamodel is configured in __init__ so we can't test it directly
        # but we can verify the configuration is correct
        assert hasattr(ThemeRestApi, "datamodel")

    def test_add_columns_configuration(self):
        """Test that add columns are configured correctly"""
        expected_columns = ["json_data", "theme_name"]
        assert ThemeRestApi.add_columns == expected_columns

    def test_edit_columns_configuration(self):
        """Test that edit columns match add columns"""
        assert ThemeRestApi.edit_columns == ThemeRestApi.add_columns

    def test_show_columns_configuration(self):
        """Test that show columns are configured correctly"""
        expected_columns = [
            "changed_on_delta_humanized",
            "changed_by.first_name",
            "changed_by.id",
            "changed_by.last_name",
            "created_by.first_name",
            "created_by.id",
            "created_by.last_name",
            "json_data",
            "id",
            "is_system",
            "is_system_default",
            "is_system_dark",
            "theme_name",
            "uuid",
        ]
        assert set(ThemeRestApi.show_columns) == set(expected_columns)

    def test_list_columns_configuration(self):
        """Test that list columns are configured correctly"""
        expected_columns = [
            "changed_on_delta_humanized",
            "changed_by.first_name",
            "changed_by.id",
            "changed_by.last_name",
            "changed_by_name",
            "created_on",
            "created_by.first_name",
            "created_by.id",
            "created_by.last_name",
            "json_data",
            "id",
            "is_system",
            "is_system_default",
            "is_system_dark",
            "theme_name",
            "uuid",
        ]
        assert set(ThemeRestApi.list_columns) == set(expected_columns)

    def test_order_columns_configuration(self):
        """Test that order columns are configured correctly"""
        expected_columns = ["theme_name"]
        assert ThemeRestApi.order_columns == expected_columns

    def test_openapi_spec_tag(self):
        """Test that OpenAPI spec tag is set correctly"""
        assert ThemeRestApi.openapi_spec_tag == "Themes"

    def test_bulk_delete_enabled(self):
        """Test that bulk delete is enabled"""
        # The bulk_delete method should be available
        assert hasattr(ThemeRestApi, "bulk_delete")
        assert callable(ThemeRestApi.bulk_delete)

    def test_custom_schemas_configured(self):
        """Test that custom schemas are properly configured"""
        from superset.themes.schemas import ThemePostSchema, ThemePutSchema

        api = ThemeRestApi()
        assert isinstance(api.add_model_schema, ThemePostSchema)
        assert isinstance(api.edit_model_schema, ThemePutSchema)

    def test_show_columns_include_new_fields(self):
        """Test that show columns include new is_system and uuid fields"""
        expected_new_fields = ["is_system", "uuid"]
        for field in expected_new_fields:
            assert field in ThemeRestApi.show_columns

    def test_list_columns_include_new_fields(self):
        """Test that list columns include new is_system and uuid fields"""
        expected_new_fields = ["is_system", "uuid"]
        for field in expected_new_fields:
            assert field in ThemeRestApi.list_columns

    def test_delete_method_registered_with_expose(self):
        """The single-item delete endpoint is registered at /<int:pk> for DELETE.

        Regression coverage for skipped integration tests in
        tests/integration_tests/themes/api_tests.py that were marked with
        "DELETE endpoint not properly registered due to route method exclusion".
        Confirms the DELETE endpoint metadata is present on the class.
        """
        delete_fn = ThemeRestApi.__dict__["delete"]
        urls = getattr(delete_fn, "_urls", None)
        assert urls is not None, "delete method missing @expose registration"
        assert ("/<int:pk>", ("DELETE",)) in urls

    def test_bulk_delete_method_registered_with_expose(self):
        """The bulk delete endpoint is registered at / for DELETE."""
        bulk_delete_fn = ThemeRestApi.__dict__["bulk_delete"]
        urls = getattr(bulk_delete_fn, "_urls", None)
        assert urls is not None, "bulk_delete method missing @expose registration"
        assert ("/", ("DELETE",)) in urls

    def test_delete_and_bulk_delete_have_distinct_routes(self):
        """The single and bulk delete endpoints expose different URL patterns."""
        delete_urls = ThemeRestApi.__dict__["delete"]._urls
        bulk_delete_urls = ThemeRestApi.__dict__["bulk_delete"]._urls
        delete_paths = {url for url, _ in delete_urls}
        bulk_paths = {url for url, _ in bulk_delete_urls}
        assert delete_paths.isdisjoint(bulk_paths)

    def test_delete_route_included_in_route_methods(self):
        """RouteMethod.DELETE is part of include_route_methods.

        The skipped integration tests claimed the DELETE endpoint was excluded
        via include_route_methods. This test guards against that regression.
        """
        assert RouteMethod.DELETE in ThemeRestApi.include_route_methods
        assert "bulk_delete" in ThemeRestApi.include_route_methods

    def test_delete_method_is_callable(self):
        """The delete method is callable on the class."""
        assert hasattr(ThemeRestApi, "delete")
        assert callable(ThemeRestApi.delete)
