"""
When pytest does test discovery, all conftest.py files found (within the 
directory strucuture over which test discovery is being done) will be run 
during the test collection phase (before any tests are run)

Therefore, this is the place to add any configuration required by the tests
(i.e. "conftest")
"""


import pytest

import os

@pytest.fixture(scope="session", autouse=True)
def set_env_archnemesis_build_name():
    os.environ['ARCHNEMESIS_BUILD_NAME'] = 'PRODUCTION'


