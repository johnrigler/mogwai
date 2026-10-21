import unittest

from fileproxy.routing import daisy_destination, split_paste


class RouteTests(unittest.TestCase):
    def test_daisy_automatic_destination_uses_current_registered_archive_only(self):
        self.assertEqual(daisy_destination(["daisy2026"], 2026), "daisy2026")
        self.assertEqual(daisy_destination(["daisy_2026"], 2026), "daisy_2026")
        self.assertEqual(daisy_destination(["daisy", "daisy2026"], 2026), "daisy")
        self.assertEqual(daisy_destination(["daisy2026", "daisy2027"], 2027), "daisy2027")
        self.assertEqual(daisy_destination(["daisy2026", "work"], 2027), "daisy")

    def test_daisy_tag(self):
        source = "https://example.org/filing.pdf"
        self.assertEqual(split_paste(source + "\n#daisy"), (source, "daisy"))

    def test_daisy_year_archive_tag(self):
        source = "https://example.org/filing.pdf"
        self.assertEqual(split_paste(source + "\n#daisy2026"), (source, "daisy2026"))

    def test_conflicting_tag(self):
        with self.assertRaises(ValueError):
            split_paste("memo #daisy #certledger")

    def test_no_url_fragment_reinterpretation(self):
        source = "https://example.org/filing#daisy"
        self.assertEqual(split_paste(source), (source, ""))


if __name__ == "__main__":
    unittest.main()
