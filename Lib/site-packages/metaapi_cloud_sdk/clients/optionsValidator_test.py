from .optionsValidator import OptionsValidator
import pytest
validator = OptionsValidator()


class TestValidateNumber:
    @pytest.mark.asyncio
    def test_validate_option(self):
        """Should validate option."""
        value = validator.validate_number(3, 5, 'opt')
        assert value == 3

    @pytest.mark.asyncio
    def test_set_option_to_default_value(self):
        """Should set option to default value if not specified."""
        value = validator.validate_number(None, 5, 'opt')
        assert value == 5

    @pytest.mark.asyncio
    def test_allow_zero_value(self):
        """Should allow zero value."""
        value = validator.validate_number(0, 5, 'opt')
        assert value == 0

    @pytest.mark.asyncio
    def test_throw_error_if_value_is_not_number(self):
        """Should throw error if value is not number."""
        try:
            validator.validate_number('test', 5, 'opt')
            raise Exception('ValidationException expected')
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'
            assert err.__str__() == 'Parameter opt must be a number, check error.details for more information'

    @pytest.mark.asyncio
    def test_throw_error_if_value_is_negative(self):
        """Should throw error if value is negative."""
        try:
            validator.validate_number(-3, 5, 'opt')
            raise Exception('ValidationException expected')
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'
            assert err.__str__() == 'Parameter opt cannot be lower than 0, check error.details for more information'


class TestValidateNonZero:
    @pytest.mark.asyncio
    def test_validate_option(self):
        """Should validate option."""
        value = validator.validate_non_zero(3, 5, 'opt')
        assert value == 3

    @pytest.mark.asyncio
    def test_set_option_to_default_value(self):
        """Should set option to default value if not specified."""
        value = validator.validate_non_zero(None, 5, 'opt')
        assert value == 5

    @pytest.mark.asyncio
    def test_throw_error_if_value_is_zero(self):
        """Should throw error if value is zero."""
        try:
            validator.validate_non_zero(0, 5, 'opt')
            raise Exception('ValidationException expected')
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'
            assert err.__str__() == 'Parameter opt must be bigger than 0, check error.details for more information'


class TestValidateBoolean:
    @pytest.mark.asyncio
    def test_validate_option(self):
        """Should validate option."""
        value = validator.validate_boolean(True, False, 'opt')
        assert value is True

    @pytest.mark.asyncio
    def test_set_option_to_default_value(self):
        """Should set option to default value if not specified."""
        value = validator.validate_boolean(None, False, 'opt')
        assert value is False

    @pytest.mark.asyncio
    def test_throw_error_if_value_is_not_boolean(self):
        """Should throw error if value is not boolean."""
        try:
            validator.validate_boolean('test', 5, 'opt')
            raise Exception('ValidationException expected')
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'
            assert err.__str__() == 'Parameter opt must be a boolean, check error.details for more information'
