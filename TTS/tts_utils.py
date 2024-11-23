def format_percentage(speed: float) -> str:
    """
    Converts a floating-point number to a percentage string in the form:
    1.0 -> "+0%", 1.1 -> "+10%", 0.9 -> "-10%", etc.
    Ensures the value stays between -50% and +50%.

    :param value: The floating-point value to format.
    :return: A string representing the percentage.
    """
    # Clamp the value to be between 0.5 and 1.5 (corresponding to -50% and +50%)
    clamped_value = max(0.5, min(1.5, speed))

    # Calculate the percentage change from 1.0
    percentage_change = (clamped_value - 1.0) * 100

    # Format the percentage with a "+" or "-" sign
    return f"{percentage_change:+.0f}%"
