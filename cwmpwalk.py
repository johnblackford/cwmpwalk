#! /usr/bin/env python3

"""
# File Name: cwmpwalk.py
#
# Description: A tool to perform a walk of a CWMP Device's Data Model
#
# Functionality:
#  - CWMPWalk:
#      A control class that performs the CWMP Data Model walk via the
#       CWMPServer and keeps a copy of the implemented data model
#  - CWMPServer:
#      A simplified CWMP Server that maintains CWMP Session state
#  - StoppableHTTPServer:
#      An HTTP Server that can be stopped when the CWMP Session is complete
#  - CWMPHandler
#      An HTTP Handler for CWMP Messages, which carries out the
#        CWMP data model walking mechanism
#  - DataModelItem
#      A generic Data Model Entity
#  - DataModelObject
#      A Data Model Object
#  - DataModelParameter
#      A Data Model Parameter
#
"""


import io
import logging
import xmltodict
import sys, getopt
import subprocess
import socket

from http.server import BaseHTTPRequestHandler, HTTPServer


# Global Constants
_VERSION = "0.1.0-alpha"



class CWMPWalk(object):
    """Utilizes a simplified CWMP Server to issue GetParameterNames
        and GetParameterValues to walk a Device's CWMP Data Model"""
    def __init__(self, ip_addr="127.0.0.1", port=8000):
        """Initialize the Object"""
        self.implemented_data_model = None
        self.cwmp = CWMPServer(ip_addr, port)


    def start_walk(self):
        """Start the CWMP Server, which walks the device's data model"""
        # Start the Server
        self.cwmp.start_server()

        # Retreive the implemented data model from the Server
        self.implemented_data_model = self.cwmp.get_implemented_data_model()


    def print_results(self):
        """Print out the implemented data model, as built out during the walk"""
        print("Testing...")
        print("")
        print("The Implemented Data Modle is:")
        for data_model_obj in self.implemented_data_model:
            print("{}".format(data_model_obj.get_name()))
            for data_model_param in data_model_obj.get_parameters():
                print("- {} = {}".format(data_model_param.get_name(), data_model_param.get_value()))


    def get_implemented_data_model(self):
        """Get the implemented data model, as built out during the walk"""
        return self.implemented_data_model



class CWMPServer(object):
    """An CWMP Server that is also an HTTP Server that can be stopped"""
    def __init__(self, ip_addr, port):
        self.port = port
        self.ip_addr = ip_addr
        self.data_model = []
        self.device_id = None
        self.root_data_model = None
        self.requested_gpn = None
        self.requested_gpv = None
        self.pending_gpn_list = []
        self.http_server = StoppableHTTPServer(("", port), CWMPHandler)
        self.http_server.set_cwmp_server(self)


    def start_server(self):
        """Keep the CWMP Server up until it is stopped"""
        starting_msg = "Starting the CWMP Server at: {}".format("http://" + self.ip_addr + ":" + str(self.port))
        logger = logging.getLogger(self.__class__.__name__)

        logger.info(starting_msg)
        print(starting_msg)

        print("Waiting for CWMP Inform...")
        self.http_server.serve_forever()


    def stop_server(self):
        """Terminate the CWMP Server"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.info("Stopping the CWMP Server")
        self.http_server.stop_serving()


    def get_device_id(self):
        """Retrieve the Device ID that is being worked on"""
        return self.device_id

    def is_device_id_present(self):
        """Check to see if the Device ID has been set"""
        return self.device_id is not None

    def set_device_id(self, value):
        """Set the Device ID for the device to be worked on"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.info("Device ID has now been set: {}".format(value))
        self.device_id = value


    def get_root_data_model(self):
        """Retrieve the Root Data Model of the device being worked on"""
        return self.root_data_model

    def set_root_data_model(self, value):
        """Set the Root Data Model for the device to be be worked on"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.debug("Root Data Model has now been set: {}".format(value))
        self.root_data_model = value


    def get_implemented_data_model(self):
        """Get the implemented data model, as built out during the walk"""
        return self.data_model

    def add_object_to_data_model(self, data_model_obj):
        """Add a Data Model Object to the implemented data model"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.info("Object [{}] has been added to the data model".format(data_model_obj.get_name()))
        self.data_model.append(data_model_obj)


    def get_requested_gpn(self):
        """Retrieve the Requested GPN that is being worked on"""
        return self.requested_gpn

    def set_requested_gpn(self, data_model_obj):
        """Set the Requested GPN to be worked on"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.debug("Requested GPN has now been set: {}".format(data_model_obj.get_name()))
        self.requested_gpn = data_model_obj


    def get_requested_gpv(self):
        """Retrieve the Requested GPV that is being worked on"""
        return self.requested_gpv

    def set_requested_gpv(self, data_model_obj):
        """Set the Requested GPV to be worked on"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.debug("Requested GPV has now been set: {}".format(data_model_obj.get_name()))
        self.requested_gpv = data_model_obj


    def append_gpn_items(self, partial_path_list):
        """Add the DataModelObject List to the end of the Pending GPN List"""
        logger = logging.getLogger(self.__class__.__name__)
        self.pending_gpn_list.extend(partial_path_list)
        logger.info("Appending {} items to the Pending GPN List".format(len(partial_path_list)))
        logger.info("There are now {} items in the Pending GPN List".format(len(self.pending_gpn_list)))

    def get_next_gpn_item(self):
        """Get the next DataModelObject item from the Pending GPN List"""
        logger = logging.getLogger(self.__class__.__name__)
        a_data_model_obj = self.pending_gpn_list.pop(0)
        logger.info("Retrieving [{}] from the Pending GPN List; {} items left".format(a_data_model_obj.get_name(), len(self.pending_gpn_list)))
        return a_data_model_obj

    def more_gpn_items(self):
        """Check to see if there are more DataModelObject items in the Pending GPN List"""
        items_in_list = False
        if len(self.pending_gpn_list) > 0:
            items_in_list = True

        return items_in_list



class StoppableHTTPServer(HTTPServer):
    """A Stoppable HTTP Server"""
    def serve_forever(self):
        """Keep the HTTP Server up until it is stopped"""
        self.stop = False
        logger = logging.getLogger(self.__class__.__name__)

        logger.info("Starting the HTTP Server")
        while not self.stop:
            logger.info("Waiting for an HTTP Request")
            self.handle_request()


    def stop_serving(self):
        """Terminate the HTTP Server"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.info("Stopping the HTTP Server")
        self.stop = True


    def get_cwmp_server(self):
        """Retrieve the value of the CWMP Server"""
        return self.cwmp_server

    def set_cwmp_server(self, value):
        """Set the value of the CWMP Server"""
        self.cwmp_server = value



class CWMPHandler(BaseHTTPRequestHandler):
    """An HTTP Request Handler for the following CWMP RPCs:
        - Inform, GetParameterNamesResponse, GetParameterValuesResponse"""
    def log_message(self, format, *args):
        """Change logging from stderr to debug log"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.debug("%s - - %s" % (self.address_string(), format % args))


    def do_GET(self):
        """Handle the HTTP GET Messages, as invalid CWMP Messages"""
        # Log the Request
        logger = logging.getLogger(self.__class__.__name__)
        logger.warning("Received incoming HTTP GET")
        logger.debug("  Path: " + self.path)

        # Respond with a 404 Error (shouldn't process GET)
        self.send_error(404, "CWMP File Not Found: %s" % self.path)


    def do_POST(self):
        """Handle the HTTP POST Messages containing CWMP Messages"""
        content = ""
        content_length = 0
        logger = logging.getLogger(self.__class__.__name__)
        cwmp_server = self.server.get_cwmp_server()

        # Process the Request
        # TODO: Should we do chunked encoding? - Might have to, or might have to front it with nginx
        if "Content-Length" in self.headers:
            content_length = int(self.headers["Content-Length"])
            content = self.rfile.read(content_length)

            # Log the Request
            logger.info("Received incoming HTTP POST")
            logger.debug("  Path: " + self.path)
            logger.debug("  Content-Length: " + str(content_length))
            logger.debug("  Content-Type: " + self.headers["Content-Type"])

            if content_length == 0:
                # Validate that this is the Empty HTTP POST that is sent after the Inform
                #  - Make sure that we have a Device ID from an Inform
                #  - Make sure that we don't have any pending GPN or GPV
                if (cwmp_server.get_requested_gpn() is None and
                        cwmp_server.get_requested_gpv() is None and
                        cwmp_server.is_device_id_present()):
                    logger.info("Processing incoming EMPTY HTTP POST as a CWMP Message")
                    self._write_incoming_cwmp_message("<EMPTY>")

                    # Start with the Root Data Model Object
                    a_data_model_obj = DataModelObject()
                    a_data_model_obj.set_name(cwmp_server.get_root_data_model() + ".")
                    a_data_model_obj.set_writable(False)

                    cwmp_server.set_requested_gpn(a_data_model_obj)

                    self._get_parameter_names(a_data_model_obj)
                else:
                    # Invalid input - return a fault
                    logger.warning("Invalid Empty POST Received")
                    self.send_error(500, "Invalid Empty POST Received")
            elif "xml" in self.headers["Content-Type"]:
                logger.info("Processing incoming HTTP POST as a CWMP Message")

                # Trace the CWMP Conversation
                self._write_incoming_cwmp_message(content)

                # Convert content from XML to Dictionary
                content_dict = self._convert_content_to_dict(content)

                # Process the CWMP Message (Inform, Empty, GPNResp, GPVResp)
                self._process_cwmp_message(content_dict["soap-env:Envelope"])
            else:
                # Invalid input - return a fault
                logger.warning(
                    "Invalid Content Type Received {} - Sending an HTTP 500"
                    .format(self.headers["Content-Type"]))
                self.send_error(500, "Invalid Content-Type: %s" % self.headers["Content-Type"])



    def _write_incoming_cwmp_message(self, message):
        """Write Incoming CWMP Trace Messages to a separate log file"""
        trace_logger = logging.getLogger("TRACE_LOGGING")
        message_type = "Incoming HTTP POST from [{}]".format(self.address_string())

        trace_logger.debug(message_type)
        # TODO: Add in a Flag that logs the contents
#        trace_logger.debug(message)



    def _write_outgoing_cwmp_message(self, message):
        """Write Outgoing CWMP Trace Messages to a separate log file"""
        trace_logger = logging.getLogger("TRACE_LOGGING")
        message_type = "Outgoing HTTP Response to [{}]".format(self.address_string())

        trace_logger.debug(message_type)
        # TODO: Add in a Flag that logs the contents
#        trace_logger.debug(message)



    def _convert_content_to_dict(self, content_str):
        """Convert the XML Content into a Dictionary"""
        content_dict = {}

        # Use these standard namespaces
        namespaces = {
            "urn:dslforum-org:cwmp-1-0": "cwmp",
            "urn:dslforum-org:cwmp-1-1": "cwmp",
            "urn:dslforum-org:cwmp-1-2": "cwmp",
            "http://www.w3.org/2001/XMLSchema": "xsd",
            "http://www.w3.org/2001/XMLSchema-instance": "xsi",
            "http://schemas.xmlsoap.org/soap/envelope/": "soap-env",
            "http://schemas.xmlsoap.org/soap/encoding/": "soap-enc"
        }

        content_dict = xmltodict.parse(content_str, process_namespaces=True, namespaces=namespaces)

        return content_dict



    def _process_cwmp_message(self, soap_envelope):
        """Process the Incoming CWMP Message, which could be one of:
             Inform, GetParameterNamesResponse, GetParameterValuesResponse"""
        soap_body = soap_envelope["soap-env:Body"]
        soap_header = soap_envelope["soap-env:Header"]
        logger = logging.getLogger(self.__class__.__name__)

        if "cwmp:Inform" in soap_body:
            logger.info("Incoming HTTP POST is a CWMP Inform RPC")
            self._process_inform(soap_header, soap_body)
        elif "cwmp:GetParameterNamesResponse" in soap_body:
            logger.info("Incoming HTTP POST is a Response to a CWMP GetParameterNames RPC")
            self._process_gpn_response(soap_body)
        elif "cwmp:GetParameterValuesResponse" in soap_body:
            logger.info("Incoming HTTP POST is a Response to a CWMP GetParameterValues RPC")
            self._process_gpv_response(soap_body)
        else:
            logger.warning("Unsupported CWMP RPC encountered - Sending an HTTP 500")
            self.send_error(500, "Unsupported CWMP RPC encountered")



    def _process_inform(self, soap_header, soap_body):
        """Process the incoming CWMP Inform RPC"""
        cwmp_server = self.server.get_cwmp_server()
        logger = logging.getLogger(self.__class__.__name__)

        # Are we already in a CWMP Session with another device?
        if cwmp_server.is_device_id_present():
            # YES; Response with a fault
            logger.warning(
                "Already Processing Device {} - Sending an HTTP 500"
                .format(cwmp_server.get_device_id()))
            self.send_error(500, "Already Processing Device: %s" % cwmp_server.get_device_id())
        else:
            # NO; Save the OUI-SN as the Found Device and send the InformResponse
            cwmp_device_id = soap_body["cwmp:Inform"]["DeviceId"]
            device_id = cwmp_device_id["OUI"] + "-" + cwmp_device_id["SerialNumber"]
            logger.info("The CWMP Inform Message is from {}".format(device_id))

            param_list = soap_body["cwmp:Inform"]["ParameterList"]
            for param_val_struct_item in param_list["ParameterValueStruct"]:
                if "SoftwareVersion" in param_val_struct_item["Name"]:
                    root_dm = param_val_struct_item["Name"].split(".")[0]
                    logger.info("The {} Device is using a {} Root Data Model".format(device_id, root_dm))
                    cwmp_server.set_root_data_model(root_dm)

            cwmp_server.set_device_id(device_id)
            self._send_inform_response(soap_header)



    def _process_gpn_response(self, soap_body):
        """Process an incoming GetParameterNames Response"""
        gpv_param_list = []
        sub_object_list = []
        cwmp_server = self.server.get_cwmp_server()
        logger = logging.getLogger(self.__class__.__name__)
        requested_data_model_obj = cwmp_server.get_requested_gpn()

        if not cwmp_server.is_device_id_present():
            # Invalid GetParameterNames Response received - respond with a fault
            logger.warning(
                "No Device ID found - Invalid GPN Response received - Sending an HTTP 500")
            self.send_error(500, "No Device ID found")
        else:
            logger.info("The CWMP GetParameterNames Response contains:")
            param_list = soap_body["cwmp:GetParameterNamesResponse"]["ParameterList"]

            if isinstance(param_list["ParameterInfoStruct"], list):
                for param_info_struct_item in param_list["ParameterInfoStruct"]:
                    dm_item = self._process_gpn_param_info_struct(param_info_struct_item)

                    if dm_item.is_object():
                        sub_object_list.append(dm_item)
                    else:
                        gpv_param_list.append(dm_item)
            else:
                dm_item = self._process_gpn_param_info_struct(param_list["ParameterInfoStruct"])

                if dm_item.is_object():
                    sub_object_list.append(dm_item)
                else:
                    gpv_param_list.append(dm_item)

            # Add the DataModelObject to the CWMP Server
            cwmp_server.add_object_to_data_model(requested_data_model_obj)

            # Add the Data Model Parameters to the DataModelObject
            for dm_param in gpv_param_list:
                requested_data_model_obj.add_parameter(dm_param)

            if len(gpv_param_list) > 0:
                # We found Parameters to Retrieve Values for
                cwmp_server.set_requested_gpv(requested_data_model_obj)
                cwmp_server.append_gpn_items(sub_object_list)

                # Send a GPV for the Parameters in the Object
                self._get_parameter_values(gpv_param_list)
            elif len(sub_object_list) > 0:
                # We didn't find Parameters to Retrieve, but we have sub-objects
                a_data_model_obj = sub_object_list.pop(0)
                cwmp_server.set_requested_gpn(a_data_model_obj)
                cwmp_server.append_gpn_items(sub_object_list)

                # Send a GPN for the Sub-Objects of this Object
                self._get_parameter_names(a_data_model_obj)
            elif cwmp_server.more_gpn_items():
                # We didn't find any Parameters or Sub-Objects, so work off the pending object list
                logger.warning("Found an empty object [{}], but still proceeding...".format(requested_data_model_obj.get_name()))
                next_gpn_obj = cwmp_server.get_next_gpn_item()
                cwmp_server.set_requested_gpn(next_gpn_obj)

                # Send a GPN for the Sub-Objects of this Object
                self._get_parameter_names(next_gpn_obj)
            else:
                # Nothing left to do, so terminate the CWMP Session
                self._terminate_cwmp_session()



    def _process_gpn_param_info_struct(self, param_info_struct_item):
        """Process the GPN ParameterInfoStruct Element"""
        dm_item = None
        is_writable = False
        param_info_name = param_info_struct_item["Name"]
        param_info_writable = param_info_struct_item["Writable"]
        logger = logging.getLogger(self.__class__.__name__)

        # Handle the different Writable Boolean Values
        if (param_info_writable == "true" or
                param_info_writable == "True" or
                param_info_writable == "1"):
            is_writable = True

        # Create either the DataModelObject or DataModelParameter
        if param_info_name.endswith("."):
            dm_item = DataModelObject()
            dm_item.set_name(param_info_name)
            dm_item.set_writable(is_writable)
            logger.info("- Sub-Object: {}".format(param_info_name))
        else:
            dm_item = DataModelParameter()
            dm_item.set_full_param_name(param_info_name)
            dm_item.set_writable(is_writable)
            logger.info("- Parameter: {}".format(param_info_name))

        return dm_item



    def _process_gpv_response(self, soap_body):
        """Process the incoming GetParameterValues Response"""
        cwmp_server = self.server.get_cwmp_server()
        logger = logging.getLogger(self.__class__.__name__)
        requested_data_model_obj = cwmp_server.get_requested_gpn()

        if not cwmp_server.is_device_id_present():
            # Invalid GetParameterParameters Response received - respond with a fault
            logger.warning(
                "No Device ID found - Invalid GPV Response received - Sending an HTTP 500")
            self.send_error(500, "No Device ID found")
        else:
            logger.info("The CWMP GetParameterParameters Response contains:")
            param_list = soap_body["cwmp:GetParameterValuesResponse"]["ParameterList"]

            if isinstance(param_list["ParameterValueStruct"], list):
                for param_value_struct_item in param_list["ParameterValueStruct"]:
                    name = param_value_struct_item["Name"]
                    value = param_value_struct_item["Value"]["#text"]
                    requested_data_model_obj.get_parameter(name).set_value(value)
            else:
                name = param_value_struct_item["Name"]
                value = param_value_struct_item["Value"]["#text"]
                requested_data_model_obj.get_parameter(name).set_value(value)

            if cwmp_server.more_gpn_items():
                next_gpn_obj = cwmp_server.get_next_gpn_item()
                cwmp_server.set_requested_gpn(next_gpn_obj)

                # Send a GPN for the Sub-Objects of this Object
                self._get_parameter_names(next_gpn_obj)
            else:
                # Nothing left to do, so terminate the CWMP Session
                self._terminate_cwmp_session()



    def _get_parameter_names(self, a_data_model_obj):
        """Send a GetParameterNames RPC to the CPE"""
        out_buffer = io.StringIO()
        logger = logging.getLogger(self.__class__.__name__)

        # Build CWMP Request
        out_buffer.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        out_buffer.write("<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">\n")
        out_buffer.write("                  xmlns:cwmp=\"urn:dslforum-org:cwmp-1-0\">\n")
        out_buffer.write(" <soapenv:Header>\n")
        out_buffer.write(" </soapenv:Header>\n")
        out_buffer.write(" <soapenv:Body>\n")
        out_buffer.write("  <cwmp:GetParameterNames>\n")
        out_buffer.write("   <ParameterPath>{}</ParameterPath>\n".format(a_data_model_obj.get_name()))
        out_buffer.write("   <NextLevel>1</NextLevel>\n")
        out_buffer.write("  </cwmp:GetParameterNames>\n")
        out_buffer.write(" </soapenv:Body>\n")
        out_buffer.write("</soapenv:Envelope>\n")

        # Send HTTP Response
        self.send_response(200)
        self.send_header("Content-type", "application/xml")
        self.end_headers()
        self.wfile.write(bytes(out_buffer.getvalue(), "utf-8"))

        logger.info("Sending a CWMP GetParameterNames for: [{}]".format(a_data_model_obj.get_name()))
        self._write_outgoing_cwmp_message(out_buffer.getvalue())

        out_buffer.close()



    def _get_parameter_values(self, param_list):
        """Send a GetParameterValues RPC to the CPE"""
        param_names = ""
        first_param = True
        out_buffer = io.StringIO()
        logger = logging.getLogger(self.__class__.__name__)

        # Build CWMP Request
        out_buffer.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        out_buffer.write("<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\"\n")
        out_buffer.write("                  xmlns:soapenc=\"http://schemas.xmlsoap.org/soap/encoding/\"\n")
        out_buffer.write("                  xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"\n")
        out_buffer.write("                  xmlns:cwmp=\"urn:dslforum-org:cwmp-1-0\">\n")
        out_buffer.write(" <soapenv:Header>\n")
        out_buffer.write(" </soapenv:Header>\n")
        out_buffer.write(" <soapenv:Body>\n")
        out_buffer.write("  <cwmp:GetParameterValues>\n")
        out_buffer.write("   <ParameterNames soapenc:arrayType=\"xsd:string[{}]\">\n".format(len(param_list)))

        # Insert the Parameters
        for param in param_list:
            if first_param:
                first_param = False
                param_names = param.get_name()
            else:
                param_names = param_names + "," + param.get_name()

            out_buffer.write("    <string>{}</string>\n".format(param.get_full_param_name()))

        # Finish the GPV
        out_buffer.write("   </ParameterNames>\n")
        out_buffer.write("  </cwmp:GetParameterValues>\n")
        out_buffer.write(" </soapenv:Body>\n")
        out_buffer.write("</soapenv:Envelope>\n")

        # Send HTTP Response
        self.send_response(200)
        self.send_header("Content-type", "application/xml")
        self.end_headers()
        self.wfile.write(bytes(out_buffer.getvalue(), "utf-8"))

        logger.info("Sending a CWMP GetParameterValues for: [{}]".format(param_names))
        self._write_outgoing_cwmp_message(out_buffer.getvalue())

        out_buffer.close()



    def _send_inform_response(self, soap_header):
        """Send an InformResponse back"""
        cwmp_id = None
        out_buffer = io.StringIO()
        logger = logging.getLogger(self.__class__.__name__)

        if "cwmp:ID" in soap_header:
            cwmp_id = soap_header["cwmp:ID"]["#text"]

        # Build CWMP Response
        out_buffer.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        out_buffer.write("<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">\n")
        out_buffer.write("                  xmlns:cwmp=\"urn:dslforum-org:cwmp-1-0\">\n")
        out_buffer.write(" <soapenv:Header>\n")

        # Include the CWMP ID if it was in the Inform
        if cwmp_id is not None:
            out_buffer.write(
                "  <cwmp:ID soapenv:mustUnderstand=\"1\">{}</cwmp:ID>\n".format(cwmp_id))

        # Finish building the CWMP Response
        out_buffer.write(" </soapenv:Header>\n")
        out_buffer.write(" <soapenv:Body>\n")
        out_buffer.write("  <cwmp:InformResponse>\n")
        out_buffer.write("   <MaxEnvelopes>1</MaxEnvelopes>\n")
        out_buffer.write("  </cwmp:InformResponse>\n")
        out_buffer.write(" </soapenv:Body>\n")
        out_buffer.write("</soapenv:Envelope>\n")

        # Send HTTP Response
        self.send_response(200)
        self.send_header("Content-type", "application/xml")
        self.end_headers()
        self.wfile.write(bytes(out_buffer.getvalue(), "utf-8"))

        logger.info("Sending a CWMP InformResponse")
        self._write_outgoing_cwmp_message(out_buffer.getvalue())

        out_buffer.close()



    def _terminate_cwmp_session(self):
        """Terminate the CWMP Session by sending an HTTP 204 response"""
        logger = logging.getLogger(self.__class__.__name__)

        # Tell the Server to stop responding to HTTP Requests
        self.server.stop_serving()

        # Send an HTTP 204 Response to terminate the CWMP Session
        self.send_response(204)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes("", "utf-8"))

        logger.info("Terminating the CWMP Session with an HTTP 204")
        self._write_outgoing_cwmp_message("<EMPTY>")



class DataModelItem(object):
    """Base class for both DataModelObject and DataModelParameter"""
    def __init__(self, is_obj):
        self.name = None
        self.writable = None
        self.is_item_an_object = is_obj


    def is_object(self):
        """Return True if this is a DataModelObject and False otherwise"""
        return self.is_item_an_object


    def get_name(self):
        """Retrieve the Data Model Item's name"""
        return self.name

    def set_name(self, value):
        """Set the name of the Data Model Item"""
        self.name = value


    def get_writable(self):
        """Retrieve the Data Model Item's Writable Property"""
        return self.writable

    def set_writable(self, value):
        """Set the Writable Property of the Data Model Item"""
        self.writable = value



class DataModelObject(DataModelItem):
    """Represents an implemented Data Model Object"""
    def __init__(self):
        """Initialize the Data Model Object"""
        super(DataModelObject, self).__init__(True)
        self.parameter_dict = {}


    def add_parameter(self, item):
        """Add a Data Model Parameter to this Data Model Object"""
        self.parameter_dict[item.get_full_param_name()] = item

    def get_parameters(self):
        """Retrieve the list of Data Model Parameters"""
        return self.parameter_dict.values()

    def get_parameter(self, param_name):
        """Retrieve a specific Data Model Parameter"""
        return self.parameter_dict[param_name]



class DataModelParameter(DataModelItem):
    """Represents an implemented Data Model Parameter"""
    def __init__(self):
        """Initialize the Data Model Parameter"""
        super(DataModelParameter, self).__init__(False)
        self.value = None
        self.full_param_name = None


    def get_value(self):
        """Retrieve the Data Model Parameter's value"""
        return self.value

    def set_value(self, value):
        """Set the value of the Data Model Parameter"""
        self.value = value


    def get_full_param_name(self):
        """Retrieve the full parameter name of the Data Model Parameter"""
        return self.full_param_name

    def set_full_param_name(self, value):
        """Set the full parameter name of the Data Model Parameter"""
        self.set_name(value.split(".")[-1])
        self.full_param_name = value




def main(argv):
    """Main CWMP Walk Tool Driver"""

    port = 8000
    interface = "en0"

    ### TODO: The file name should probably be absolute instead of relative
    ###         (based on standard install location?)
    logging.basicConfig(filename="logs/cwmpwalk.log",
                        format='%(asctime)-15s %(name)s %(levelname)-8s %(message)s')
    logging.getLogger().setLevel(logging.INFO)

    logging.info("#######################################################")
    logging.info("## Starting cwmpwalk.py                              ##")
    logging.info("#######################################################")

    # Usage string for input argument handling
    usage_str = "cwmpwalk.py [-p <CWMP ACS URL Port>]"

    # Retrieve the input arguments
    logging.info("Processing the Input Arguments...")
    logging.debug("Found Input Arguments: {}".format(argv))

    try:
        opts, args = getopt.getopt(argv, "hi:p:", "intf, port")
    except getopt.GetoptError:
        print("Error Encountered:")
        logging.error("Error Encountered:")
        print(" - Unknown command line argument encountered")
        logging.error(" - Unknown command line argument encountered")
        print("")
        print(usage_str)
        sys.exit(2)


    # Process the input arguments
    for opt, arg in opts:
        if opt in ('-h', "--help"):
            print(usage_str)
            print("  -i|--intf     :: System Interface (e.g. 'en0') to run the CWMP ACS on")
            print("  -p|--port     :: Port to run the CWMP ACS on")
            print("  -V|--version  :: Print the version of the tool")
            sys.exit()
        elif opt in ("-i", "--intf"):
            interface = arg
        elif opt in ("-p", "--port"):
            port = int(arg)
        elif opt in ("-V", "--version"):
            print("Report Tool :: version={}".format(_VERSION))
            sys.exit()


    # Main logic
    walker = CWMPWalk(_get_ip_address(interface), port)
    walker.start_walk()
    walker.print_results()


def _get_ip_address(netdev='en0'):
    """Retrieve the IP Address"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("gmail.com",80))
        addr = s.getsockname()[0]

    return addr




if __name__ == "__main__":
    main(sys.argv[1:])

