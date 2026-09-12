import unittest

from optech_fr import normalize_newsletter_reference_labels


class NormalizeNewsletterReferenceLabelsTests(unittest.TestCase):
    def test_adds_article_after_voir(self):
        source = "(voir [Bulletin #364][news364 ldk attribution])"
        expected = "(voir le [Bulletin #364][news364 ldk attribution])"
        self.assertEqual(normalize_newsletter_reference_labels(source), expected)

    def test_adds_article_to_multiline_link_with_escaped_hash(self):
        source = "dans [Bulletin\n  \\#419][news419 hwi]"
        expected = "dans le [Bulletin\n  \\#419][news419 hwi]"
        self.assertEqual(normalize_newsletter_reference_labels(source), expected)

    def test_preserves_existing_determiners(self):
        examples = (
            "voir le [Bulletin #419][news419 hwi]",
            "une modification du [Bulletin #419][news419 hwi]",
            "décrit au [Bulletin #419][news419 hwi]",
            "consulter ce [Bulletin #419][news419 hwi]",
            "dans un [Bulletin #419][news419 hwi]",
        )
        for source in examples:
            with self.subTest(source=source):
                self.assertEqual(normalize_newsletter_reference_labels(source), source)

    def test_translates_english_link_label_and_adds_article(self):
        source = "voir [Newsletter #382][news382 bc33629]"
        expected = "voir le [Bulletin #382][news382 bc33629]"
        self.assertEqual(normalize_newsletter_reference_labels(source), expected)

    def test_capitalizes_article_at_sentence_start(self):
        source = "[Bulletin #419][news419 hwi] décrit le changement."
        expected = "Le [Bulletin #419][news419 hwi] décrit le changement."
        self.assertEqual(normalize_newsletter_reference_labels(source), expected)


if __name__ == "__main__":
    unittest.main()
