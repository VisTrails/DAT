import logging
import os, os.path
import sys
import traceback


def main():
    root_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..'))

    # Attempt to import this very file
    try:
        import dat.main
    except ImportError:
        sys.path.insert(0, root_dir)
        try:
            import dat.main
        except ImportError:
            sys.stderr.write("Error: unable to find the dat Python package\n")
            sys.exit(1)

    dat.main.application_path = root_dir

    # Attempt to import VisTrails
    vistrails_root = os.getenv('VISTRAILS_ROOT')
    if vistrails_root is not None:
        logging.info("Adding VISTRAILS_ROOT to the Python path: %s" %
                     vistrails_root)
        sys.path.append(vistrails_root)
    try:
        import core
    except ImportError:
        if vistrails_root is not None:
            sys.stderr.write("Couldn't import VisTrails.\n"
                             "A VISTRAILS_ROOT environment variable is set, "
                             "but VisTrails couldn't be\nimported from "
                             "there.\n"
                             "Please update or remove it.\n")
            sys.exit(1)
        sys.path.append(os.path.abspath(
                os.path.join(os.path.dirname(__file__),
                             '../vistrails/vistrails')))
        try:
            import core
        except ImportError:
            sys.stderr.write("Error: unable to find VisTrails.\n"
                             "Make sure it is installed correctly, or set the "
                             "VISTRAILS_ROOT environment\nvariable.\n")
            sys.exit(1)

    try:
        import gui.application
        sys.exit(gui.application.start())
    except Exception:
        sys.stderr.write("Critical: Application exiting with an exception:\n")
        traceback.print_exc(file=sys.stderr)


if __name__ == '__main__':
    main()
