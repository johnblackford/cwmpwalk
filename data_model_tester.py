#! /usr/bin/env python

"""
# File Name: data_model_tester.py
#
# Description: Data Model Tester
#
# Functionality:
#  - DataModelSanityTester:
#     A concrete Tester that performs a sanity check on the implemented
#     data model for a Device by walking it via GetParameterNames and
#     GetParameterValues RPC calls.  Essentialy it is that starting point
#     of an ID-106 Test Client
#  - This is an example of how cwmpwalk.py could be used
#
"""


import sys
sys.path.append("../report-tool")

import logging

from cwmpwalk import CWMPWalk
from nodes import Document



class DataModelSanityTester(object):
    """A contrete Tester that performs a Data Model Sanity Check via
        an HTTP Request Handler"""
    def __init__(self):
        """Initialize the Tester"""
        self.implemented_data_model = None
        self.cwmp_walker = CWMPWalk(port=8000)


    def test(self):
        """Test the implemented data model"""
        # Start the Server
        self.cwmp_walker.start_walk()

        # Retreive the implemented data model from the CWMPWalk instance
        self.implemented_data_model = self.cwmp_walker.get_implemented_data_model()

        print "Testing..."
        print ""
        print "The Implemented Data Model is:"
        for data_model_obj in self.implemented_data_model:
            print "{}".format(data_model_obj.get_name())
            for data_model_param in data_model_obj.get_parameters():
                print "- {} = {}".format(data_model_param.get_name(), data_model_param.get_value())




if __name__ == "__main__":
    logging.basicConfig(filename="logs/cwmp-testing.log",
                        format='%(asctime)-15s %(name)s %(levelname)-8s %(message)s')
    logging.getLogger().setLevel(logging.INFO)

    myDoc = Document()

    tester = DataModelSanityTester()
    tester.test()
