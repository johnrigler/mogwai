import unittest

from fileproxy import server


class CompatibilityTests(unittest.TestCase):
    def test_handler_keeps_legacy_endpoints(self):
        handler = server.make_handler("/tmp/fileproxy-test-unconfigured.json", "/tmp/fileproxy-index-unconfigured.json")
        self.assertTrue(issubclass(handler, server.chisel.Handler))
        self.assertTrue(callable(handler.do_GET))
        self.assertTrue(callable(handler.do_POST))
        self.assertTrue(callable(server.chisel.Handler.do_GET))
        self.assertTrue(callable(server.chisel.Handler.do_POST))


if __name__ == "__main__":
    unittest.main()
