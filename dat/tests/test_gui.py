"""Tests for the dat.gui package.

"""


import unittest
import warnings


class CallRecorder(object):
    def __init__(self, func=None):
        self.calls = []
        self._func = func

    def __call__(self, *args, **kwargs):
        self.calls.append((list(args), kwargs))
        if self._func is not None:
            return self._func(*args, **kwargs)


class Test_gui(unittest.TestCase):
    def test_unique_varname(self):
        from dat.gui.load_variable_dialog import unique_varname
        self.assertEqual(unique_varname('variable'), 'variable (2)')
        self.assertEqual(unique_varname('variable (4)'), 'variable (5)')

    def test_translate(self):
        from PyQt4 import QtCore
        old_translate = QtCore.QCoreApplication.translate
        try:
            QtCore.QCoreApplication.translate = cr = CallRecorder(
                    old_translate)
    
            from dat.gui import translate
            tr = translate(Test_gui)
            self.assertIsNotNone(tr)
            msg = u"Don't translate "
            msg += u"me (unittest)" # there is no way xgettext can find this

            self.assertEqual(tr(msg), msg)
            call1 = (
                    [
                            'dat.tests.test_gui.Test_gui',
                            msg,
                            None,
                            QtCore.QCoreApplication.UnicodeUTF8],
                    dict())
            self.assertEqual(cr.calls, [call1])

            tr = translate('this test')
            self.assertEqual(tr(msg, "disambiguation"), msg)
            call2 = (
                    [
                            'this test',
                            msg,
                            "disambiguation",
                            QtCore.QCoreApplication.UnicodeUTF8],
                    dict())
            self.assertEqual(cr.calls, [call1, call2])
        finally:
            QtCore.QCoreApplication.translate = old_translate

    def test_notifications(self):
        from dat.gui.application import NotificationDispatcher
        nd = NotificationDispatcher()
        class C(object): pass
        with warnings.catch_warnings(record=True) as w:
            notif1 = CallRecorder()
            nd.register_notification('notif_A', notif1)
            # registered to non-existing notification
            self.assertEqual(len(w), 1)

            notif2 = CallRecorder()
            nd.register_notification('notif_A', notif2)

            nd.send_notification('notif_A', 'hello', 'world', rep=42)
            first_call = (['hello', 'world'], dict(rep=42))
            self.assertEqual(notif1.calls, [first_call])
            self.assertEqual(notif2.calls, [first_call])

            nd.unregister_notification('notif_A', notif2)
            nd.send_notification('notif_A', 'second', nb=2)
            second_call = (['second'], dict(nb=2))
            self.assertEqual(notif1.calls, [first_call, second_call])
            self.assertEqual(notif2.calls, [first_call])

            nd.builderWindow = C()
            viewA, viewB = C(), C()
            nd.builderWindow.current_view = viewA

            fakeWindow = C()
            nd.create_notification('notif_B')
            self.assertEqual(len(w), 1)
            nd.create_notification('notif_B')
            # notification created twice
            self.assertEqual(len(w), 2)
            nd.create_notification('notif_B', window=fakeWindow)
            nd.create_notification('notif_B', view=viewA)
            nd.create_notification('notif_B', view=viewB)
            notif3 = CallRecorder()
            nd.register_notification('notif_B', notif3,
                                     window=fakeWindow)
            notif4 = CallRecorder()
            self.assertEqual(len(w), 2)
            nd.register_notification('notif_B', notif4,
                                     window=nd.builderWindow)
            # registered to non-existing notification
            self.assertEqual(len(w), 3)
            notif5 = CallRecorder()
            nd.register_notification('notif_B', notif5)
            notif6 = CallRecorder()
            nd.register_notification('notif_B', notif6,
                                     view=viewA)
            notif7 = CallRecorder()
            nd.register_notification('notif_B', notif7,
                                     view=viewB)
            nd.send_notification('notif_B', 'third')
            third_call = (['third'], dict())

            self.assertEqual(notif1.calls, [first_call, second_call])
            self.assertEqual(notif2.calls, [first_call])
            self.assertEqual(notif3.calls, [])
            self.assertEqual(notif4.calls, [third_call])
            self.assertEqual(notif5.calls, [third_call])
            self.assertEqual(notif6.calls, [third_call])
            self.assertEqual(notif7.calls, [])

            self.assertEqual(len(w), 3)
            nd.unregister_notification('notif_A', notif7)
            # unregistered non-registered method
            self.assertEqual(len(w), 4)
            nd.unregister_notification('notif_B', notif6,
                                       view=viewA)
            nd.send_notification('notif_B', nb=4)
            self.assertEqual(len(w), 4)
            self.assertEqual(notif6.calls, [third_call])
