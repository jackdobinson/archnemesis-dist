"""
When pytest does test discovery, all conftest.py files found (within the 
directory strucuture over which test discovery is being done) will be run 
during the test collection phase (before any tests are run)

Therefore, this is the place to add any configuration required by the tests
(i.e. "conftest")
"""

import os
#import pytest

#print('RUN CONFTEST')



SESSION_ENV={
    'ARCHNEMESIS_BUILD_NAME' : 'PRODUCTION'
}

_ENV_PREV = dict()


def pytest_configure(config):
    #print('IN pytest_configure')
    pass

def pytest_unconfigure(config):
    #print('IN pytest_unconfigure')
    pass

def pytest_sessionstart(session):
    #print('IN pytest_sessionstart')
    print('PYTEST :: Setting environment variables for test session:')
    for k,v in SESSION_ENV.items():
        _ENV_PREV[k] = os.environ.get(k,None)
        os.environ[k] = v
        print(f'PYTEST ::     {k}="{v}"')

def pytest_sessionfinish(session, exitstatus):
    #print('IN pytest_sessionfinish')
    for k,v in _ENV_PREV.items():
        if v is None:
            # then environment variable was not set, so delete it
            del os.environ[k]
        else:
            os.environ[k] = v
