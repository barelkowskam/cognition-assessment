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

from unittest.mock import Mock, patch

import pytest

from superset.commands.theme.delete import DeleteThemeCommand
from superset.commands.theme.exceptions import (
    SystemThemeInUseError,
    SystemThemeProtectedError,
    ThemeNotFoundError,
)
from superset.commands.theme.seed import SeedSystemThemesCommand
from superset.commands.theme.update import UpdateThemeCommand
from superset.models.core import Theme
from tests.conftest import with_config


class TestUpdateThemeCommand:
    """Unit tests for UpdateThemeCommand"""

    @patch("superset.commands.theme.update.ThemeDAO")
    def test_validate_theme_not_found(self, mock_theme_dao):
        """Test validation fails when theme doesn't exist"""
        # Arrange
        mock_theme_dao.find_by_id.return_value = None
        command = UpdateThemeCommand(123, {"theme_name": "test"})

        # Act & Assert
        with pytest.raises(ThemeNotFoundError):
            command.validate()

    @patch("superset.commands.theme.update.ThemeDAO")
    def test_validate_system_theme_protection(self, mock_theme_dao):
        """Test validation fails when trying to update system theme"""
        # Arrange
        mock_theme = Mock(spec=Theme)
        mock_theme.is_system = True
        mock_theme_dao.find_by_id.return_value = mock_theme
        command = UpdateThemeCommand(123, {"theme_name": "test"})

        # Act & Assert
        with pytest.raises(SystemThemeProtectedError):
            command.validate()

    @patch("superset.commands.theme.update.ThemeDAO")
    def test_validate_regular_theme_success(self, mock_theme_dao):
        """Test validation succeeds for regular (non-system) themes"""
        # Arrange
        mock_theme = Mock(spec=Theme)
        mock_theme.is_system = False
        mock_theme_dao.find_by_id.return_value = mock_theme
        command = UpdateThemeCommand(123, {"theme_name": "test"})

        # Act
        command.validate()  # Should not raise any exception

        # Assert
        assert command._model == mock_theme

    @patch("superset.commands.theme.update.ThemeDAO")
    def test_run_success(self, mock_theme_dao):
        """Test successful theme update"""
        # Arrange
        mock_theme = Mock(spec=Theme)
        mock_theme.is_system = False
        mock_updated_theme = Mock(spec=Theme)
        mock_theme_dao.find_by_id.return_value = mock_theme
        mock_theme_dao.update.return_value = mock_updated_theme

        command = UpdateThemeCommand(123, {"theme_name": "updated_name"})

        # Act
        result = command.run()

        # Assert
        assert result == mock_updated_theme
        mock_theme_dao.update.assert_called_once_with(
            mock_theme, {"theme_name": "updated_name"}
        )


class TestSeedSystemThemesCommand:
    """Unit tests for SeedSystemThemesCommand"""

    @with_config(
        {
            "THEME_DEFAULT": None,
            "THEME_DARK": None,
        }
    )
    def test_run_no_themes_configured(self, app):
        """Test run when no themes are configured"""
        # Arrange
        command = SeedSystemThemesCommand()

        # Act
        command.run()  # Should complete without error

    @with_config(
        {
            "THEME_DEFAULT": {"algorithm": "default", "token": {}},
            "THEME_DARK": None,
        }
    )
    @patch("superset.commands.theme.seed.db")
    def test_run_with_theme_default_only(self, mock_db, app):
        """Test run when only THEME_DEFAULT is configured"""
        # Arrange
        mock_session = Mock()
        mock_db.session = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        command = SeedSystemThemesCommand()

        # Act
        command.run()

        # Assert
        mock_session.add.assert_called_once()
        # Note: commit is handled by @transaction() decorator, not directly called

    @with_config(
        {
            "THEME_DEFAULT": {"algorithm": "default", "token": {}},
            "THEME_DARK": None,
        }
    )
    @patch("superset.commands.theme.seed.db")
    def test_run_update_existing_theme(self, mock_db, app):
        """Test run when theme already exists and needs updating"""
        # Arrange
        # Mock existing theme
        mock_existing_theme = Mock(spec=Theme)
        mock_existing_theme.json_data = '{"old": "data"}'

        mock_session = Mock()
        mock_db.session = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_existing_theme
        )

        command = SeedSystemThemesCommand()

        # Act
        command.run()

        # Assert
        assert '"algorithm": "default"' in mock_existing_theme.json_data
        # Note: commit is handled by @transaction() decorator, not directly called
        mock_session.add.assert_not_called()  # Should not add new theme

    @with_config(
        {
            "THEME_DEFAULT": {"algorithm": "default", "token": {}},
            "THEME_DARK": None,
        }
    )
    @patch("superset.commands.theme.seed.db")
    @patch("superset.commands.theme.seed.logger")
    def test_run_handles_database_error(self, mock_logger, mock_db, app):
        """Test run handles database errors gracefully"""
        # Arrange
        mock_session = Mock()
        mock_db.session = mock_session
        mock_session.query.side_effect = Exception("Database error")

        command = SeedSystemThemesCommand()

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            command.run()  # Should raise exception due to @transaction() decorator

    @with_config(
        {
            "THEME_DEFAULT": {"algorithm": "default", "token": {}},
            "THEME_DARK": {"algorithm": "dark", "token": {}},
        }
    )
    @patch("superset.commands.theme.seed.db")
    def test_run_with_both_themes(self, mock_db, app):
        """Test run when both THEME_DEFAULT and THEME_DARK are configured"""
        # Arrange
        mock_session = Mock()
        mock_db.session = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        command = SeedSystemThemesCommand()

        # Act
        command.run()

        # Assert
        assert mock_session.add.call_count == 2  # Both themes should be added
        # Note: commit is handled by @transaction() decorator, not directly called

    def test_validate(self):
        """Test validate method (should be no-op)"""
        # Arrange
        command = SeedSystemThemesCommand()

        # Act & Assert
        command.validate()  # Should complete without error


class TestDeleteThemeCommand:
    """Unit tests for DeleteThemeCommand"""

    @staticmethod
    def _make_theme(
        theme_id: int = 1,
        is_system: bool = False,
        is_system_default: bool = False,
        is_system_dark: bool = False,
    ) -> Mock:
        """Build a Theme mock with the boolean flags relevant to delete validation."""
        theme = Mock(spec=Theme)
        theme.id = theme_id
        theme.is_system = is_system
        theme.is_system_default = is_system_default
        theme.is_system_dark = is_system_dark
        return theme

    @patch("superset.commands.theme.delete.ThemeDAO")
    def test_validate_no_themes_found(self, mock_theme_dao):
        """Test validation fails when no themes match the requested ids"""
        # Arrange
        mock_theme_dao.find_by_ids.return_value = []
        command = DeleteThemeCommand([42])

        # Act & Assert
        with pytest.raises(ThemeNotFoundError):
            command.validate()
        mock_theme_dao.find_by_ids.assert_called_once_with([42])

    @patch("superset.commands.theme.delete.ThemeDAO")
    def test_validate_partial_match_raises_not_found(self, mock_theme_dao):
        """Test validation fails when only some of the requested ids exist"""
        # Arrange — caller asked for two ids but DAO only resolves one
        mock_theme_dao.find_by_ids.return_value = [self._make_theme(theme_id=1)]
        command = DeleteThemeCommand([1, 2])

        # Act & Assert
        with pytest.raises(ThemeNotFoundError):
            command.validate()

    @patch("superset.commands.theme.delete.ThemeDAO")
    def test_validate_system_theme_protection(self, mock_theme_dao):
        """Test validation fails when any of the themes is a system theme"""
        # Arrange
        mock_theme_dao.find_by_ids.return_value = [
            self._make_theme(theme_id=1),
            self._make_theme(theme_id=2, is_system=True),
        ]
        command = DeleteThemeCommand([1, 2])

        # Act & Assert
        with pytest.raises(SystemThemeProtectedError):
            command.validate()

    @patch("superset.commands.theme.delete.ThemeDAO")
    def test_validate_blocks_system_default_theme(self, mock_theme_dao):
        """Test validation fails when a theme is set as the system default"""
        # Arrange
        mock_theme_dao.find_by_ids.return_value = [
            self._make_theme(theme_id=1, is_system_default=True),
        ]
        command = DeleteThemeCommand([1])

        # Act & Assert
        with pytest.raises(SystemThemeInUseError):
            command.validate()

    @patch("superset.commands.theme.delete.ThemeDAO")
    def test_validate_blocks_system_dark_theme(self, mock_theme_dao):
        """Test validation fails when a theme is set as the system dark theme"""
        # Arrange
        mock_theme_dao.find_by_ids.return_value = [
            self._make_theme(theme_id=1, is_system_dark=True),
        ]
        command = DeleteThemeCommand([1])

        # Act & Assert
        with pytest.raises(SystemThemeInUseError):
            command.validate()

    @patch("superset.commands.theme.delete.db")
    @patch("superset.commands.theme.delete.ThemeDAO")
    def test_validate_regular_theme_success(self, mock_theme_dao, mock_db):
        """Test validation succeeds for regular (non-system, unused) themes"""
        # Arrange
        themes = [
            self._make_theme(theme_id=1),
            self._make_theme(theme_id=2),
        ]
        mock_theme_dao.find_by_ids.return_value = themes
        # No dashboards reference these themes
        dashboard_query = mock_db.session.query.return_value.filter.return_value
        dashboard_query.all.return_value = []

        command = DeleteThemeCommand([1, 2])

        # Act
        command.validate()  # Should not raise

        # Assert
        assert command._models == themes
        assert command._dashboard_usage == {}
        assert command.get_dashboard_usage() == {}

    @patch("superset.commands.theme.delete.db")
    @patch("superset.commands.theme.delete.ThemeDAO")
    def test_validate_collects_dashboard_usage(self, mock_theme_dao, mock_db):
        """Test validation populates dashboard usage for themes in use"""
        # Arrange
        themes = [
            self._make_theme(theme_id=1),
            self._make_theme(theme_id=2),
        ]
        mock_theme_dao.find_by_ids.return_value = themes
        dashboard_query = mock_db.session.query.return_value.filter.return_value
        dashboard_query.all.return_value = [
            (1, "Sales Overview"),
            (1, "Marketing"),
            (2, "Engineering"),
        ]

        command = DeleteThemeCommand([1, 2])

        # Act
        command.validate()

        # Assert
        assert command.get_dashboard_usage() == {
            1: ["Sales Overview", "Marketing"],
            2: ["Engineering"],
        }

    @patch("superset.commands.theme.delete.db")
    @patch("superset.commands.theme.delete.ThemeDAO")
    def test_run_deletes_and_dissociates_dashboards(self, mock_theme_dao, mock_db):
        """Test successful run dissociates dashboards and delegates to DAO.delete"""
        # Arrange
        themes = [self._make_theme(theme_id=1)]
        mock_theme_dao.find_by_ids.return_value = themes
        # Two dashboards currently reference theme id=1
        dashboard_filter = mock_db.session.query.return_value.filter.return_value
        dashboard_filter.count.return_value = 2
        dashboard_filter.all.return_value = [
            (1, "Sales Overview"),
            (1, "Marketing"),
        ]
        dashboard_filter.update.return_value = 2

        command = DeleteThemeCommand([1])

        # Act
        command.run()

        # Assert — dashboards are unlinked before the delete call
        dashboard_filter.update.assert_called_once()
        mock_theme_dao.delete.assert_called_once_with(themes)

    def test_get_dashboard_usage_defaults_to_empty(self):
        """Test get_dashboard_usage returns an empty dict when validate hasn't run"""
        command = DeleteThemeCommand([1])
        assert command.get_dashboard_usage() == {}
