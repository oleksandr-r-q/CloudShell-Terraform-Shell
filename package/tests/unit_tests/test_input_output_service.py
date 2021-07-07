from unittest import TestCase
from unittest.mock import Mock, MagicMock

from cloudshell.iac.terraform.services.input_output_service import InputOutputService, TFVar


class TestInputOutputService(TestCase):

    def test_try_decrypt_password_for_unencrypted_value(self):
        # arrange
        driver_helper = Mock()
        driver_helper.api.DecryptPassword.side_effect = Exception()
        input_output_service = InputOutputService(driver_helper)
        value = Mock()

        # act
        result = input_output_service.try_decrypt_password(value)

        # assert
        self.assertEqual(value, result)

    def test_try_decrypt_password_for_encrypted_value(self):
        # arrange
        api_result = Mock()
        driver_helper = Mock()
        driver_helper.api.DecryptPassword.return_value = api_result
        input_output_service = InputOutputService(driver_helper)
        value = Mock()

        # act
        result = input_output_service.try_decrypt_password(value)

        # assert
        self.assertEqual(api_result.Value, result)

    def test_get_variables_from_var_attributes_model_name_contains_uppercase(self):
        def return_original_val(*args, **kwargs):
            return args[0]

        # arrange
        driver_helper = Mock()
        driver_helper.tf_service.cloudshell_model_name = "TF Service"
        var_name = f"{driver_helper.tf_service.cloudshell_model_name}.var_MyVar"
        driver_helper.tf_service.attributes = {"attribute1": "val1",
                                               "attribute2": "val2",
                                               var_name: "val3"}
        input_output_service = InputOutputService(driver_helper)
        input_output_service.try_decrypt_password = Mock(side_effect=return_original_val)

        # act
        result = input_output_service.get_variables_from_var_attributes()

        # assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "MyVar")
        self.assertEqual(result[0].value, "val3")

    def test_get_variables_from_terraform_input_attribute(self):
        # arrange
        driver_helper = Mock()
        tf_inputs_attr = f"{driver_helper.tf_service.cloudshell_model_name}.Terraform Inputs"
        driver_helper.tf_service.attributes = {tf_inputs_attr: "key1=val1,key2 = val2, key3=val3"}
        input_output_service = InputOutputService(driver_helper)

        # act
        result = input_output_service.get_variables_from_terraform_input_attribute()

        # assert
        self.assertEqual(len(result), 3)
        self.assertIn(TFVar("key1", "val1"), result)
        self.assertIn(TFVar("key2", "val2"), result)
        self.assertIn(TFVar("key3", "val3"), result)

    def test_get_variables_from_terraform_input_attribute_doesnt_exist(self):
        # arrange
        driver_helper = Mock()
        driver_helper.tf_service.attributes = MagicMock()
        input_output_service = InputOutputService(driver_helper)

        # act
        result = input_output_service.get_variables_from_terraform_input_attribute()

        # assert
        self.assertEqual(len(result), 0)

    def test_parse_and_save_outputs_no_mapped_attributes_and_no_outputs_attribute(self):
        # arrange
        driver_helper = Mock()
        driver_helper.tf_service.attributes = MagicMock()
        input_output_service = InputOutputService(driver_helper)

        # act
        input_output_service.parse_and_save_outputs({})

        # assert
        driver_helper.api.SetServiceAttributesValues.assert_not_called()

    def test_parse_and_save_outputs_with_mapped_attributes(self):
        # arrange
        driver_helper = Mock()
        var_name = f"{driver_helper.tf_service.cloudshell_model_name}.out_MyVar"
        driver_helper.tf_service.attributes = {
            var_name: "val1"
        }
        json_output = {
          "MyVar": {
            "sensitive": False,
            "type": "string",
            "value": "val1"
          }
        }
        input_output_service = InputOutputService(driver_helper)

        # act
        input_output_service.parse_and_save_outputs(json_output)

        # assert
        driver_helper.api.SetServiceAttributesValues.assert_called_once()
        self.assertEqual(driver_helper.api.SetServiceAttributesValues.mock_calls[0].args[2][0].Name, var_name)
        self.assertEqual(driver_helper.api.SetServiceAttributesValues.mock_calls[0].args[2][0].Value, "val1")

    def test_parse_and_save_outputs_with_mapped_attributes_and_outputs_attribute(self):
        # arrange
        driver_helper = Mock()
        var_name = f"{driver_helper.tf_service.cloudshell_model_name}.out_MyVar1"
        tf_output_name = f"{driver_helper.tf_service.cloudshell_model_name}.Terraform Outputs"
        driver_helper.tf_service.attributes = {
            var_name: "val1",
            tf_output_name: ""
        }
        json_output = {
            "MyVar1": {
                "sensitive": False,
                "type": "string",
                "value": "val1"
            },
            "MyVar2": {
                "sensitive": False,
                "type": "string",
                "value": "val2"
            },
            "MyVar3": {
                "sensitive": False,
                "type": "string",
                "value": "val3"
            }
        }
        input_output_service = InputOutputService(driver_helper)

        # act
        input_output_service.parse_and_save_outputs(json_output)

        # assert
        driver_helper.api.SetServiceAttributesValues.assert_called_once()
        # check that SetServiceAttributesValues was called with 2 AttributeNameValue values
        self.assertEqual(len(driver_helper.api.SetServiceAttributesValues.mock_calls[0].args[2]), 2)

    def test_parse_and_save_outputs_with_sensitive_unmapped_attributes(self):
        # arrange
        driver_helper = Mock()
        tf_output_name = f"{driver_helper.tf_service.cloudshell_model_name}.Terraform Outputs"
        driver_helper.tf_service.attributes = {
            tf_output_name: ""
        }
        json_output = {
            "MyVar2": {
                "sensitive": True,
                "type": "string",
                "value": "val2"
            },
            "MyVar3": {
                "sensitive": False,
                "type": "string",
                "value": "val3"
            }
        }
        input_output_service = InputOutputService(driver_helper)

        # act
        input_output_service.parse_and_save_outputs(json_output)

        # assert
        driver_helper.api.SetServiceAttributesValues.assert_called_once()
        # check that the sensitive value is masked
        attribute_update_req = driver_helper.api.SetServiceAttributesValues.mock_calls[0].args[2][0]
        self.assertIn("MyVar2=(sensitive)", attribute_update_req.Value)
        self.assertNotIn("val2", attribute_update_req.Value)

