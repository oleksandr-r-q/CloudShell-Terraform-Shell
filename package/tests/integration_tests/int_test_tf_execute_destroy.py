import os
from unittest import TestCase

from tests.constants import SHELL_NAME
from tests.integration_tests.helper_objects.integration_context import IntegrationData


class TestTerraformExecuteDestroy(TestCase):
    def setUp(self) -> None:
        self.integration_data = IntegrationData()

    def test_execute_and_destroy(self):
        self.integration_data.context.resource.attributes[f"{SHELL_NAME}.Terraform Inputs"] = \
            os.environ.get(" VAULT_TF_INPUTS")
        self.integration_data.context.resource.attributes[
            f"{SHELL_NAME}.Github Terraform Module URL"] = os.environ.get("GITHUB_TF_PRIVATE_AZUREAPP_URL")
        self.integration_data.context.resource.attributes[
            f"{SHELL_NAME}.UUID"] = ""

        self.integration_data.context.real_api.ClearSandboxData(self.integration_data._driver_helper.sandbox_id)

        self.integration_data.driver.execute_terraform(self.integration_data.context)

        # As UUID has been created and SB data now contains UUID and Status we must update context so destroy can run
        # And also replace the custom inputs and TF URL
        self.integration_data.set_context_resource_attributes()
        self.integration_data.context.resource.attributes[f"{SHELL_NAME}.Terraform Inputs"] = \
            os.environ.get(" VAULT_TF_INPUTS")
        self.integration_data.context.resource.attributes[
            f"{SHELL_NAME}.Github Terraform Module URL"] = os.environ.get("GITHUB_TF_PRIVATE_VAULT_URL")

        self.integration_data.driver.destroy_terraform(self.integration_data.context)

