import argparse
import os
import sys
import unittest

from flake8.main import application

# set environment variables before importing app code so it connects to the test database
os.environ['DB_NAME'] = 'trestle_test'
os.environ['DB_USER'] = 'trestle_test'
os.environ['DB_PASS'] = 'trestle_test'


def lint():
    # cli options at http://flake8.pycqa.org/en/latest/user/options.html
    # error code definitions at https://pep8.readthedocs.io/en/latest/intro.html
    print('Running linter...') # NOQA: T001
    app = application.Application()
    app.run([
        '--exclude=.git,__pycache__,node_modules,static,svelte,views',
        '--ignore=E128,E261,W503',
        '--max-line-length=120',
        '.',
    ])
    print('Linting complete.') # NOQA: T001
    # app.exit() # could just call this but it exits early whereas we might want to do other things
    return app.result_count < 1 and not app.catastrophic_failure


def unit(test_path=None):

    loader = unittest.loader.TestLoader()
    if test_path and test_path.endswith('.py'):
        # support testing only a single file, called like `python tests path/to/test.py`
        suite = loader.loadTestsFromName(test_path.replace(os.sep, '.').replace('.py', ''))
    else:
        suite = loader.discover('tests')

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('test_path', nargs='?')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-l', '--lint', action='store_true', help='only run the linter')
    group.add_argument('-u', '--unit', action='store_true', help='only run unit tests')
    args = parser.parse_args()

    lint_success = unit_success = True

    if args.lint:
        lint_success = lint()
    elif args.unit:
        unit_success = unit(test_path=args.test_path)
    else:
        lint_success = lint()
        unit_success = unit(test_path=args.test_path)

    # the function calls return success or not
    # but exit codes are 0 (false) for success and anything else (true) for failure
    sys.exit(not lint_success or not unit_success)
