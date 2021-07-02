from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.driver_context import InitCommandContext, ResourceCommandContext
from cloudshell.shell.core.session.logging_session import LoggingSessionContext

from data_model import *  # run 'shellfoundry generate' to generate data model classes
from subprocess import check_output
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext

from downloaders.downloader import Downloader
from driver_helper_obj import DriverHelperObject

from services import input_output_service
from services.input_output_service import InputOutputService
from services.provider_handler import ProviderHandler
from services.sb_data_handler import SbDataHandler
from services.tf_proc_exec import TfProcExec


class TerraformService2GDriver (ResourceDriverInterface):

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        pass

    def initialize(self, context):
        """
        Initialize the driver session, this function is called everytime a new instance of the driver is created
        This is a good place to load and cache the driver configuration, initiate sessions etc.
        :param InitCommandContext context: the context the command runs on
        """

        pass

    def cleanup(self):
        """
        Destroy the driver session, this function is called everytime a driver instance is destroyed
        This is a good place to close any open sessions, finish writing to log files
        """
        pass

    def execute_terraform(self, context: ResourceCommandContext):
        with LoggingSessionContext(context) as logger:

            api = CloudShellSessionContext(context).get_api()
            res_id = context.reservation.reservation_id
            tf_service = TerraformService2G.create_from_context(context)

            driver_helper_obj = DriverHelperObject(api, res_id, tf_service, logger)

            downloader = Downloader(driver_helper_obj)
            tf_workingdir = downloader.download_terraform_module()
            downloader.download_terraform_executable(tf_workingdir)

            tf_proc_executer = TfProcExec(driver_helper_obj,
                                          SbDataHandler(driver_helper_obj, tf_workingdir),
                                          InputOutputService(driver_helper_obj))
            if tf_proc_executer.can_execute_run():
                ProviderHandler.initialize_provider(driver_helper_obj)
                tf_proc_executer.init_terraform()
                tf_proc_executer.plan_terraform()
                tf_proc_executer.apply_terraform()
                tf_proc_executer.save_terraform_outputs()
            else:
                err_msg = "Execution is not enabled due to either failed previous Execution (*Try Destroy first) or " \
                          "Successfully executed previously without successfully destroying it first"
                api.WriteMessageToReservationOutput(
                    res_id,err_msg

                )
                raise Exception(err_msg)

    def destroy_terraform(self, context):
        with LoggingSessionContext(context) as logger:

            api = CloudShellSessionContext(context).get_api()
            res_id = context.reservation.reservation_id
            tf_service = TerraformService2G.create_from_context(context)

            driver_helper_obj = DriverHelperObject(api, res_id, tf_service, logger)
            sb_data_handler = SbDataHandler(driver_helper_obj)

            if sb_data_handler.get_tf_working_dir():
                ProviderHandler.initialize_provider(driver_helper_obj)
                tf_proc_executer = TfProcExec(driver_helper_obj, sb_data_handler, InputOutputService(driver_helper_obj))
                if tf_proc_executer.can_destroy_run():
                    tf_proc_executer.destroy_terraform()
                else:
                    raise Exception("Destroy blocked because APPLY was not yet executed")
            else:
                raise Exception("Destroy blocked due to missing state file")
