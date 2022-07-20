from .errorHandler import ValidationException


class OptionsValidator:
    """Class for validating API options."""

    def validate_number(self, value: int or float or None, default_value: int or float, name: str):
        """Validates a number parameter.

        Args:
            value: Value to validate.
            default_value: Default value for an option.
            name: Option name.

        Returns:
            Validated value.

        Raises:
            ValidationException: If value is invalid.
        """
        if value is None:
            return default_value
        if (not isinstance(value, int)) and (not isinstance(value, float)):
            raise ValidationException(f'Parameter {name} must be a number')
        if value < 0:
            raise ValidationException(f'Parameter {name} cannot be lower than 0')
        return value

    def validate_non_zero(self, value: int or float or None, default_value: int or float, name: str):
        """Validates a number parameter to be above zero.

        Args:
            value: Value to validate.
            default_value: Default value for an option.
            name: Option name.

        Returns:
            Validated value.

        Raises:
            ValidationException: If value is invalid.
        """
        value = self.validate_number(value, default_value, name)
        if value == 0:
            raise ValidationException(f'Parameter {name} must be bigger than 0')
        return value

    def validate_boolean(self, value: bool or None, default_value: bool, name: str):
        """Validates a number parameter.

        Args:
            value: Value to validate.
            default_value: Default value for an option.
            name: Option name.

        Returns:
            Validated value.

        Raises:
            ValidationException: If value is invalid.
        """
        if value is None:
            return default_value
        if not isinstance(value, bool):
            raise ValidationException(f'Parameter {name} must be a boolean')
        return value
