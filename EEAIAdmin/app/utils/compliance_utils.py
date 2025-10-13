import logging
import re

logger = logging.getLogger(__name__)


def check_compliance(data, compliance_rules):
    """
    Perform a compliance check on the provided data using predefined rules.

    Args:
        data (str or dict): The data to validate (e.g., transaction details, user query, or document content).
        compliance_rules (list): A list of compliance rules or keywords to check against.

    Returns:
        dict: Compliance results indicating whether the data complies and any violations found.
    """
    logger.info("Starting compliance check...")
    violations = []

    try:
        # Check if the data matches any compliance rules
        if isinstance(data, str):
            for rule in compliance_rules:
                if re.search(rule, data, re.IGNORECASE):
                    violations.append(f"Violation of rule: {rule}")
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    for rule in compliance_rules:
                        if re.search(rule, value, re.IGNORECASE):
                            violations.append(f"Violation in {key}: {rule}")

        # Return compliance status and violations
        if violations:
            logger.warning(f"Compliance violations found: {violations}")
            return {"compliant": False, "violations": violations}

        logger.info("Data is compliant with all rules.")
        return {"compliant": True, "violations": None}

    except Exception as e:
        logger.error(f"Error during compliance check: {e}")
        return {"compliant": False, "violations": ["Error during compliance check."]}


def sanitize_user_input(input_string):
    """
    Sanitize user input by removing special characters to prevent SQL injection or other issues.

    Args:
        input_string (str): The input string to sanitize.

    Returns:
        str: Sanitized string.
    """
    try:
        sanitized_string = re.sub(r"[^a-zA-Z0-9\s]", "", input_string)
        logger.info(f"Sanitized input: {sanitized_string}")
        return sanitized_string
    except Exception as e:
        logger.error(f"Error sanitizing user input: {e}")
        return input_string


def apply_additional_compliance_checks(data, additional_checks):
    """
    Apply additional compliance checks on data.

    Args:
        data (str or dict): The data to validate.
        additional_checks (dict): Dictionary of custom checks with conditions and error messages.

    Returns:
        dict: Results indicating compliance and any violations.
    """
    logger.info("Applying additional compliance checks...")
    violations = []

    try:
        for field, check in additional_checks.items():
            if isinstance(data, dict) and field in data:
                value = data[field]
                if not check["condition"](value):
                    violations.append(f"{field}: {check['error_message']}")

        if violations:
            logger.warning(f"Additional compliance violations: {violations}")
            return {"compliant": False, "violations": violations}

        logger.info("Data passed additional compliance checks.")
        return {"compliant": True, "violations": None}

    except Exception as e:
        logger.error(f"Error during additional compliance checks: {e}")
        return {"compliant": False, "violations": ["Error during additional compliance checks."]}
