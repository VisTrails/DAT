import logging
import os, os.path
import sys


def main():
    # Attempt to import this very file
    try:
        import dat.main
    except ImportError:
        sys.path.insert(
            0,
            os.path.abspath(
                    os.path.join(os.path.dirname(__file__), '..')))
        try:
            import dat.main
        except ImportError:
            sys.stderr.write("Error: unable to find the dat Python package\n")
            sys.exit(1)

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

    import gui.application
    gui.application.start()


if __name__ == '__main__':
    main()
