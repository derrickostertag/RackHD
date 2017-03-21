'''
Copyright 2017, Dell Emc

Author(s):

FIT test script template

Test Script summary:
put something herex`
'''

import fit_path  # NOQA: unused import
import unittest
import json


# import nose decorator attr
from nose.plugins.attrib import attr

# Import nosedep if dependencies are needed between tests
from nosedep import depends

# Import the logging feature
import flogging

from common import fit_common

# set up the logging
logs = flogging.get_loggers()

# Define the test group here using unittest @attr
# @attr is a decorator and must be located in the line just above the class to be labeled
#   These can be any label to run groups of tests selectively
#   When setting regression or smoke to True, the test must meet CI requirements


@attr(regression=False, smoke=False, scaleio_group=True)
class deploy_scaleio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # class method is run once per script
        # usually not required in the script
        cls.nodes = []

    def setUp(self):
        # setUp is run for each test
        logs.info("  **** Running test: %s", self._testMethodName)
        self.__nodes = fit_common.node_select() 

    def shortDescription(self):
        # This removes the docstrings (""") from the unittest test list (collect-only)
        return None


#    @depends(after=test_first)
    def test_get_nodes(self):
        """
        This test is an example of using fit_common.node_select to retrieve a node list.
        For demo purposes, it needs communication to a running rackhd instance or will fail.
        """
        nodes = []
        # Retrive list of nodes, default gets compute nodes
        nodes = fit_common.node_select()

        # Check if any nodes returned
        self.assertNotEqual([], nodes, msg=("No Nodes in List"))

        # Log the list of nodes
        logs.info(" %s", json.dumps(nodes, indent=4))

#    @depends(after=test_get_nodes)
    def test_get_nodes_rackhdapi(self):
        """
        This test is an example of using fit_common.rackhdapi() to perform an API call
        and using data from the response.
        For demo purposes, it needs communication to a running rackhd instance.
        """
        nodes = []
        nodelist = []

        # Perform an API call
        api_data = fit_common.rackhdapi('/api/2.0/nodes')

        # Check return status is what you expect
        status = api_data.get('status')
        self.assertEqual(status, 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        # Use the response data
        try:
            nodes = api_data.get('json')
        except:
            self.fail("No Json data in repsonse")
        for node in nodes:
            nodelist.append(node.get('id'))
        logs.info(" %s", json.dumps(nodelist, indent=4))

        # example to set the class level nodelist
        self.__class__.nodes = nodelist


    def test_deploy_scaleio(self, options=None, payloadFile=None):
        with open("./tests/scaleio/scaleio_deploy_payload_example.json") as payload_file:
            payload = json.load(payload_file)

        print json.dumps(payload, indent=4)

        node = self.__nodes[0]

        result = fit_common.rackhdapi('/api/2.0/nodes/'
                                      + node +
                                      '/workflows', action='post', payload=payload)

        self.assertEqual(result['status'], 201,
                         'Was expecting code 201. Got ' + str(result['status']))

        graphId = result['json']['context']['graphId']

        retries = 60
        for dummy in range(0, retries):
            result = fit_common.rackhdapi('/api/2.0/workflows/' + graphId, action='get')
            if result['json']['status'] == 'running' or result['json']['status'] == 'Running':
                if fit_common.VERBOSITY >= 2:
                    # Add print out of workflow
                    print "Graph state: {}".format(result['json']['status'])
                fit_common.time.sleep(10)
            elif result['json']['status'] == 'succeeded':
                if fit_common.VERBOSITY >= 2:
                    print "Workflow state: {}".format(result['json']['status'])
                break 
            else:
                if fit_common.VERBOSITY >= 2:
                    print "Workflow state (unknown): {}".format(result['json']['status'])
                break

        print "Graph finished  with the following state: " + result['json']['status']


        self.assertEqual(result['json']['status'], 'succeeded',
                         'Was expecting succeeded. Got ' + result['json']['status'])


    def test_uninstall_scaleio(self, options=None, payloadFile=None):
        payload = {
            "name": "Graph.Uninstall.ScaleIo",
            "options": {
                "defaults": {
                    "path": "/tmp",
                    "username": "root",
                    "password": "onrack",
                    "host": "172.31.128.120"
                }
            }
        }

        node = self.__nodes[0]

        for host in ['172.31.128.120', '172.31.128.130', '172.31.128.140']:
             payload['options']['defaults']['host'] = host

             result = fit_common.rackhdapi('/api/2.0/nodes/'
                                           + node +
                                           '/workflows', action='post', payload=payload)

             self.assertEqual(result['status'], 201,
                              'Was expecting code 201. Got ' + str(result['status']))

             graphId = result['json']['context']['graphId']

             retries = 60
             for dummy in range(0, retries):
                 result = fit_common.rackhdapi('/api/2.0/workflows/' + graphId, action='get')
                 if result['json']['status'] == 'running' or result['json']['status'] == 'Running':
                     if fit_common.VERBOSITY >= 2:
                         # Add print out of workflow
                         print "Graph state: {}".format(result['json']['status'])
                     fit_common.time.sleep(2)
                 elif result['json']['status'] == 'succeeded':
                     if fit_common.VERBOSITY >= 2:
                         print "Workflow state: {}".format(result['json']['status'])
                     break
                 else:
                     if fit_common.VERBOSITY >= 2:
                         print "Workflow state (unknown): {}".format(result['json']['status'])
                     break

             print "Graph finished  with the following state: " + result['json']['status']

             self.assertEqual(result['json']['status'], 'succeeded',
                              'Was expecting succeeded. Got ' + result['json']['status'])

if __name__ == '__main__':
    unittest.main()
