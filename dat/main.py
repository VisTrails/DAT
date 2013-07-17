import os
import sys
import traceback


application_path = None


def set_sip_api():
    import sip
    api2_classes = [
            'QData', 'QDateTime', 'QString', 'QTextStream',
            'QTime', 'QUrl', 'QVariant',
            ]
    for cl in api2_classes:
        sip.setapi(cl, 2)


def setup_vistrails():
    """Locates VisTrails and fixes the path.

    This function is also used to setup the tests, that is why it is separate
    from main().
    """
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

    # Setup PyQt4
    set_sip_api()

    # VisTrails location
    vistrails_root = os.getenv('VISTRAILS_ROOT')
    if vistrails_root is None:
        vistrails_root = os.path.join(root_dir, 'vistrails')

    # Clean up the PYTHONPATH, because we don't want Vistrails sources to be
    # directly accessible or something like that
    # Shouldn't cause issues, unless there are third-party libraries installed
    # inside the DAT source tree (why would you do that?)
    i = 0
    while i < len(sys.path):
        path = os.path.realpath(sys.path[i])
        if path != root_dir and path.startswith(root_dir):
            sys.path.pop(i)
        else:
            i += 1

    sys.path.insert(0, vistrails_root)


def main():
    """Entry point for DAT.
    """
    setup_vistrails()

    try:
        import dat.gui.application
        v = dat.gui.application.start()
        dat.gui.application.stop()
        sys.exit(v)
    except Exception:
        sys.stderr.write("Critical: Application exiting with an exception:\n")
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
