import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.localize_newsletter_links import Resolver, process_text, run


class LocalNewsletterLinkTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        self.en = "/en/newsletters/2019/03/05/"
        self.fr = "/fr/newsletters/2019/03/05/"

    def page(self, lang, body):
        path = self.repo / "_site" / lang / "newsletters/2019/03/05/index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'<main><article>{body}</article></main>', encoding="utf-8")

    def french_source(self):
        path = self.repo / "_posts/fr/newsletters/2019-03-05-newsletter.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    def translated_pages(self):
        self.french_source()
        self.page("en", '<h2 id="news">News</h2><ul><li id="outage">Outage</li></ul>')
        self.page("fr", '<h2 id="nouvelles">Nouvelles</h2><ul><li id="panne">Panne</li></ul>')

    def test_same_batch_link_is_repaired_offline_and_is_idempotent(self):
        self.translated_pages()
        resolver = Resolver(self.repo, {})
        text = f"[Bulletin #36][news36]\n[news36]: {self.en}#outage\n"
        updated, report = process_text(text, resolver, True)
        self.assertIn(self.fr + "#panne", updated)
        self.assertEqual(report[0]["mode"], "aligned_outline")
        self.assertEqual(process_text(updated, resolver, True), (updated, []))

    def test_published_target_with_same_anchor_preserves_query(self):
        self.french_source()
        self.page("fr", '<ul><li id="lnd-2448">LND</li></ul>')
        result = Resolver(self.repo, {}).resolve(self.en + "?view=full#lnd-2448")
        self.assertEqual(result["to"], self.fr + "?view=full#lnd-2448")

    def test_base_link_and_absolute_bitcoinops_url(self):
        self.translated_pages()
        updated, _ = process_text(f"[voir](https://bitcoinops.org{self.en})", Resolver(self.repo, {}), True)
        self.assertEqual(updated, f"[voir]({self.fr})")

    def test_missing_translation_is_allowed_but_missing_render_is_not(self):
        resolver = Resolver(self.repo, {})
        self.assertEqual(resolver.resolve(self.en)["reason"], "fr_source_missing")
        self.french_source()
        self.assertEqual(resolver.resolve(self.en)["status"], "unresolved")

    def test_structure_drift_requires_override(self):
        self.translated_pages()
        self.page("fr", '<h2 id="nouvelles">Nouvelles</h2><h3 id="extra">Extra</h3>'
                        '<ul><li id="panne">Panne</li></ul>')
        self.assertEqual(Resolver(self.repo, {}).resolve(self.en + "#outage")["status"], "unresolved")
        resolver = Resolver(self.repo, {"2019-03-05": {"outage": "panne"}})
        self.assertEqual(resolver.resolve(self.en + "#outage")["to"], self.fr + "#panne")

    def test_wrong_override_and_missing_source_anchor_are_rejected(self):
        self.translated_pages()
        resolver = Resolver(self.repo, {"2019-03-05": {"outage": "absent"}})
        self.assertEqual(resolver.resolve(self.en + "#outage")["status"], "unresolved")
        self.assertEqual(Resolver(self.repo, {}).resolve(self.en + "#unknown")["status"], "unresolved")

    def test_reordered_shared_anchors_are_not_mapped_by_position(self):
        self.french_source()
        self.page("en", '<ul><li id="a"></li><li id="b"></li><li id="en"></li></ul>')
        self.page("fr", '<ul><li id="b"></li><li id="a"></li><li id="fr"></li></ul>')
        self.assertEqual(Resolver(self.repo, {}).resolve(self.en + "#en")["status"], "unresolved")

    def test_duplicate_anchors_are_rejected(self):
        self.french_source()
        self.page("fr", '<h2 id="news"></h2><h2 id="news"></h2>')
        self.assertEqual(Resolver(self.repo, {}).resolve(self.en)["status"], "unresolved")

    def test_online_repair_leaves_newsletters_to_local_resolver(self):
        from tools.repair_fr_links import localize_internal_links

        with patch("tools.repair_fr_links.resolve_internal_url",
                   return_value=("/fr/topics/test/", {"status": "resolved"})) as online:
            updated, _ = localize_internal_links(self.en + " /en/topics/test/", skip_newsletters=True)
        self.assertEqual(updated, self.en + " /fr/topics/test/")
        online.assert_called_once_with("/en/topics/test/")

    def test_metadata_comments_and_code_are_preserved(self):
        self.translated_pages()
        protected = (f"---\nsource: {self.en}\n---\n"
                     f"```markdown\n[link]({self.en})\n```\n"
                     f"<!-- {self.en} -->\n{{% comment %}}{self.en}{{% endcomment %}}\n"
                     f"`{self.en}`\nhttps://other.example{self.en}\n"
                     f"  ~~~markdown\n  [link]({self.en})\n  ~~~\n")
        self.assertEqual(process_text(protected, Resolver(self.repo, {}), True), (protected, []))

    def test_audit_fails_on_convertible_links_and_apply_does_not_partially_write(self):
        self.translated_pages()
        batch = self.repo / "batch"
        batch.mkdir()
        first = batch / "2019-03-12-newsletter.md"
        first.write_text(self.en + "#outage", encoding="utf-8")
        _, failed = run(self.repo, batch, {}, False)
        self.assertTrue(failed)
        original = first.read_text()
        second = batch / "2019-03-19-newsletter.md"
        second.write_text(self.en + "#unknown", encoding="utf-8")
        _, failed = run(self.repo, batch, {}, True)
        self.assertTrue(failed)
        self.assertEqual(first.read_text(), original)
        second.unlink()
        _, failed = run(self.repo, batch, {}, True)
        self.assertFalse(failed)
        self.assertEqual(first.read_text(), self.fr + "#panne")
        self.assertFalse(run(self.repo, batch, {}, False)[1])


if __name__ == "__main__":
    unittest.main()
