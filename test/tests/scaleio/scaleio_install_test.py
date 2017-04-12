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
import os
import test_api_utils

# import nose decorator attr
from nose.plugins.attrib import attr

# Import nosedep if dependencies are needed between tests
from nosedep import depends

# Import the logging feature
import flogging

from common import fit_common

# set up the logging
logs = flogging.get_loggers()
PAYLOAD = []

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

    def test_build_solution_pack(self):
        """
        This test is an example of using fit_common.rackhdapi() to perform an API call
        and using data from the response.
        For demo purposes, it needs communication to a running rackhd instance.
        """
        global PAYLOAD
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
            nodetype = node['type']
            if nodetype == "compute":
                nodeid = node['id']
                nodename = test_api_utils.get_rackhd_nodetype(nodeid)
                if nodename == "Quanta T41":
                    nodelist.append(nodeid)

        configfile = fit_common.json.loads(open("../../solution-pack/scaleio/payload/scaleio_payload_template.json").read())

        for key, value in configfile.items():
            if key == "options":
                for subkey, subvalue in value.items():
                    if subvalue["graphOptions"]["target"] == "master_node_id":
                        subvalue["graphOptions"]["target"] = nodelist[0]
                    elif subvalue["graphOptions"]["target"] == "standby_node_id":
                        subvalue["graphOptions"]["target"] = nodelist[1]
                    elif subvalue["graphOptions"]["target"] == "tie_breaker_node_id":
                        subvalue["graphOptions"]["target"] = nodelist[2]
                    else :
                        print 'Invalid target string = "{0}"'.format(subvalue["graphOptions"]["target"])

        PAYLOAD = json.dumps(configfile, indent=4)
        with open('../../solution-pack/scaleio/payload/payload.json', 'w') as outfile:
            outfile.write(json.dumps(configfile, indent=4))
            outfile.write('\n')

        # Build Solution Package
        os.chdir("../../solution-pack/scaleio")
        os.system("./build_solution_pack.sh")

    @fit_common.unittest.skip("Skipping test_deploy_scaleio_no_payload")
    def test_deploy_scaleio_no_payload(self, options=None, payloadFile=None):
        node = self.__nodes[0]

        result = fit_common.rackhdapi('/api/2.0/nodes/'
                                      + node +
                                      '/workflows', action='post')

        self.assertEqual(result['status'], 400,
                         'Was expecting code 400. Got ' + str(result['status']))

    @fit_common.unittest.skip("Skipping test_deploy_scaleio_bad_payload")
    def test_deploy_scaleio_bad_payload(self, options=None, payloadFile=None):
        with open("./tests/scaleio/scaleio_deploy_payload_bad.json") as payload_file:
            payload = json.load(payload_file)

        print json.dumps(payload, indent=4)

        node = self.__nodes[0]

        result = fit_common.rackhdapi('/api/2.0/nodes/'
                                      + node +
                                      '/workflows', action='post', payload=PAYLOAD)

        self.assertEqual(result['status'], 201,
                         'Was expecting code 201. Got ' + str(result['status']))

        graphId = result['json']['context']['graphId']

        retries = 30
        for dummy in range(0, retries):
            result = fit_common.rackhdapi('/api/2.0/workflows/' + graphId, action='get')
            if result['json']['status'] == 'running' or result['json']['status'] == 'Running':
                if fit_common.VERBOSITY >= 2:
                    # Add print out of workflow
                    print 'Graph name="{0}"; Graph state="{1}"'.format(result['json']['tasks'][0]['label'], result['json']['status'])
                fit_common.time.sleep(5)
            elif result['json']['status'] == 'succeeded':
                if fit_common.VERBOSITY >= 2:
                    print "Workflow state: {}".format(result['json']['status'])
                break 
            else:
                if fit_common.VERBOSITY >= 2:
                    print "Workflow state (unknown): {}".format(result['json']['status'])
                break

        print "Graph finished  with the following state: " + result['json']['status']


        self.assertEqual(result['json']['status'], 'failed',
                         'Was expecting failed. Got ' + str(result['json']['status']))

    @depends(after=test_build_solution_pack)
#    @fit_common.unittest.skip("Skipping test_deploy_solution_pack")
    def test_deploy_solution_pack(self, options=None, payloadFile=None):
        node = self.__nodes[0]

        filename = fit_common.scp_file_to_host("../../solution-pack/scaleio/scaleio.tar.gz")
        print 'Copy "{}" to Host complete'.format(filename)

        self.assertEqual(fit_common.remote_shell('tar xzvf scaleio.tar.gz')['exitcode'],
                         0, "Untar failure")

        print 'Untar "{}" complete'.format(filename)

        deploy_command = './scripts/deploy.sh ' + node
        print deploy_command

        self.assertEqual(fit_common.remote_shell(deploy_command)['exitcode'],
                         0, "Deploy failure")

        print 'Deploying ScaleIO Solution Pack'


    @depends(after=test_build_solution_pack)
    @fit_common.unittest.skip("Skipping test_deploy_scaleio")
    def test_deploy_scaleio(self, options=None, payloadFile=None):
        with open("../../solution-pack/scaleio/payload/payload.json") as payload_file:
            payload = json.load(payload_file)

       # print json.dumps(payload, indent=4)
        print PAYLOAD

        node = self.__nodes[0]
        print node

        result = fit_common.rackhdapi('/api/2.0/nodes/'
                                      + node +
                                      '/workflows', action='post', payload=payload)

        self.assertEqual(result['status'], 201,
                         'Was expecting code 201. Got ' + str(result['status']))

        graphId = result['json']['context']['graphId']

        retries = 240
        for dummy in range(0, retries):
            result = fit_common.rackhdapi('/api/2.0/workflows/' + graphId, action='get')
            if result['json']['status'] == 'running' or result['json']['status'] == 'Running':
                if fit_common.VERBOSITY >= 2:
                    # Add print out of workflow
                    #print 'Graph name="{0}"; Graph state="{1}"'.format(result['json']['tasks'][0]['label'], result['json']['status'])
                    print 'GraphID ="{0}"; Status="{1}"'.format(graphId, result['json']['status'])
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

    @fit_common.unittest.skip("Skipping test_uninstall_scaleio")
#    @depends(after=test_deploy_scaleio)
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
                         print 'Graph name="{0}"; Graph state="{1}"'.format(result['json']['tasks'][0]['label'], result['json']['status'])
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
