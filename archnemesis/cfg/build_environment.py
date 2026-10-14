import os

KNOWN_BUILD_NAMES = ('DEVELOPMENT', 'PRODUCTION')

BUILD_NAME = os.environ.get('ARCHNEMESIS_BUILD_NAME', 'PRODUCTION')


if BUILD_NAME not in KNOWN_BUILD_NAMES:
    raise ValueError(f'archnemsis.cfg.build_environment.BUILD_NAME must be one of {KNOWN_BUILD_NAMES}')