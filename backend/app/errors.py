class ProviderError(RuntimeError):
    """A generation step failed in a way the user should see."""


class ProviderNotConfigured(ProviderError):
    """A provider exists but its model, workflow or service is not set up yet."""
