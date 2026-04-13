"""Dedicated exceptions for the provisioning service (Portfolio Engine)."""
from uuid import UUID


class ProvisioningSubscriptionNotFoundError(Exception):
    def __init__(self, subscription_id: UUID):
        self.subscription_id = subscription_id
        super().__init__(f"ProductSubscription {subscription_id} not found")


class InvalidSubscriptionStateError(Exception):
    def __init__(self, subscription_id: UUID, current_status: str):
        self.subscription_id = subscription_id
        self.current_status = current_status
        super().__init__(
            f"ProductSubscription {subscription_id} must be 'pending' but is '{current_status}'"
        )


class AlreadyProvisionedError(Exception):
    def __init__(self, subscription_id: UUID, portfolio_id: UUID):
        self.subscription_id = subscription_id
        self.portfolio_id = portfolio_id
        super().__init__(
            f"ProductSubscription {subscription_id} already has portfolio {portfolio_id}"
        )


class ProvisioningTemplateNotFoundError(Exception):
    def __init__(self, template_id: UUID):
        self.template_id = template_id
        super().__init__(f"PortfolioTemplate {template_id} not found")


class TemplateProductMismatchError(Exception):
    def __init__(self, template_id: UUID, template_product_id: UUID, subscription_product_id: UUID):
        self.template_id = template_id
        self.template_product_id = template_product_id
        self.subscription_product_id = subscription_product_id
        super().__init__(
            f"Template {template_id} belongs to product {template_product_id}, "
            f"but subscription references product {subscription_product_id}"
        )


class ClientNotEligibleError(Exception):
    def __init__(self, client_id: UUID, reason: str):
        self.client_id = client_id
        self.reason = reason
        super().__init__(f"Client {client_id} is not eligible: {reason}")


class InactiveProductError(Exception):
    def __init__(self, product_id: UUID, current_status: str):
        self.product_id = product_id
        self.current_status = current_status
        super().__init__(f"Product {product_id} must be 'active' but is '{current_status}'")
