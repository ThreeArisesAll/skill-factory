"""Public-contract failure types shared by the internal pipeline modules."""


class ContractError(ValueError):
    """Raised when a request or package violates the public contract."""
