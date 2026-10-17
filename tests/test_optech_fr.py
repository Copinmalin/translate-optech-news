import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from optech_fr import load_preferences, normalize_headings, normalize_newsletter_reference_labels, process_one


class NormalizeHeadingsTests(unittest.TestCase):
    def setUp(self):
        self.headings = load_preferences()["headings"]

    def test_enforces_fixed_titles_despite_translated_variants(self):
        source = "## Action items\n\n## News\n\n## Notable code and documentation changes\n"
        translated = "## Actions à réaliser\n\n## Actualités\n\n## Modifications importantes\n"
        expected = (
            "## Mesures à prendre\n\n## Nouvelles\n\n"
            "## Changements notables dans le code et la documentation\n"
        )
        self.assertEqual(normalize_headings(translated, self.headings, source), expected)

    def test_preserves_historical_heading_levels_anchors_and_closing_hashes(self):
        source = "### Action items {#actions} ###\n### News\n## Notable code changes\n"
        translated = "### Actions {#autre} ###\n### Actualités\n## Changements importants\n"
        expected = (
            "### Mesures à prendre {#actions} ###\n### Nouvelles\n"
            "## Changements notables dans le code\n"
        )
        self.assertEqual(normalize_headings(translated, self.headings, source), expected)

    def test_preserves_custom_titles_body_links_and_code_blocks(self):
        source = "## News\n## Special topic\n"
        untouched = (
            "Voir [News][news].\n[news]: /en/newsletters/2022/01/01/#news\n\n"
            "```markdown\n## News\n```\n~~~\n## Action items\n~~~\n"
        )
        translated = "## Actualités\n## Sujet spécial\n" + untouched
        self.assertEqual(
            normalize_headings(translated, self.headings, source),
            "## Nouvelles\n## Sujet spécial\n" + untouched,
        )

    def test_rejects_missing_extra_or_changed_level_headings(self):
        for translated in ("## Actualités\n", "## Actualités\n## Actions\n## Autre\n",
                           "## Actualités\n### Actions\n"):
            with self.subTest(translated=translated), self.assertRaises(ValueError):
                normalize_headings(translated, self.headings, "## News\n## Action items\n")

    def test_normalizes_english_titles_without_source_and_preserves_blank_lines(self):
        self.assertEqual(
            normalize_headings("### Action items\n\n\n## News", self.headings),
            "### Mesures à prendre\n\n\n## Nouvelles",
        )

    def test_is_idempotent(self):
        source = "## Action items\n## News\n"
        result = normalize_headings("## Actions requises\n## Actualités\n", self.headings, source)
        self.assertEqual(normalize_headings(result, self.headings, source), result)

    def test_process_one_enforces_titles_before_saving_without_api_calls(self):
        source = "---\ntitle: 'Bitcoin Optech Newsletter #36'\n---\n## Action items\n## News\n"
        with tempfile.TemporaryDirectory() as directory, \
             patch("optech_fr.os.getenv", return_value="offline-test"), \
             patch("optech_fr.fetch", return_value=SimpleNamespace(text=source)), \
             patch("optech_fr.translate_body_with_openai", return_value="## Actions\n## Actualités\n"):
            result = process_one("https://bitcoinops.org/en/newsletters/2019/03/05/", Path(directory), "unused")
            self.assertEqual(result["status"], "ok", result)
            content = Path(result["output"]).read_text(encoding="utf-8")
            self.assertIn("## Mesures à prendre\n## Nouvelles\n", content)

    def test_process_one_does_not_save_a_structurally_invalid_translation(self):
        source = "---\ntitle: 'Bitcoin Optech Newsletter #36'\n---\n## Action items\n## News\n"
        with tempfile.TemporaryDirectory() as directory, \
             patch("optech_fr.os.getenv", return_value="offline-test"), \
             patch("optech_fr.fetch", return_value=SimpleNamespace(text=source)), \
             patch("optech_fr.translate_body_with_openai", return_value="## Actualités\n"):
            result = process_one("https://bitcoinops.org/en/newsletters/2019/03/05/", Path(directory), "unused")
            self.assertEqual(result["status"], "error")
            self.assertIn("titres Markdown", result["error"])
            self.assertEqual(list(Path(directory).rglob("*.md")), [])


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
