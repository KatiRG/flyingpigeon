import nose.tools
from nose import SkipTest
from nose.plugins.attrib import attr

from malleefowl import wpsclient

import __init__ as base

def setup():
    pass

@attr('online')   
def test_analogs():
    result = wpsclient.execute(
        service = base.SERVICE,
        identifier = "eobs_to_cordex",
        inputs = [ ('var_eobs', 'tn') ],
        outputs = [('ncout', True)],
        verbose=False,
        sleep_secs=120,
        )

    nose.tools.ok_(result['status'] == 'ProcessSucceeded', result)
    nose.tools.ok_(len(result['processOutputs']) == 3, result)
    #nose.tools.ok_(False, result)
    