import unittest
import server

def entry(name, group="personal", content=""):
    return dict(name=name, slug=name, group=group, content=content)

class ReferenceTests(unittest.TestCase):
    def test_generic_words_need_explicit_markup(self):
        entries = {"a": entry("alpha-skill",content="Some documents and images."), "b":entry("documents")}
        self.assertEqual(server.reference_edges(entries), {})
        entries["a"]["content"]="Use `documents`."
        self.assertTrue(server.reference_edges(entries)[("a","b")]["forward"])

    def test_duplicate_names_are_not_arbitrarily_resolved(self):
        entries={"a":entry("alpha-skill","personal","Use beta-skill."),
                 "b":entry("beta-skill","one"),"c":entry("beta-skill","two")}
        self.assertEqual(server.reference_edges(entries),{})
        entries["b"]["group"]="personal"
        self.assertIn(("a","b"),server.reference_edges(entries))

    def test_identity_and_frontmatter_do_not_create_relations(self):
        entries={"a":entry("alpha-skill",content="---\nname: alpha-skill\ndescription: beta-skill\n---\n# alpha-skill"),
                 "b":entry("beta-skill"),"c":entry("alpha-skill","plugin")}
        self.assertEqual(server.reference_edges(entries),{})

    def test_reverse_mentions_preserve_both_directions(self):
        edges=server.reference_edges({"a":entry("alpha-skill",content="Use beta-skill."),"b":entry("beta-skill",content="Use alpha-skill.")})
        self.assertEqual(len(edges),1)
        self.assertTrue(edges[("a","b")]["forward"] and edges[("a","b")]["backward"])

if __name__ == "__main__":
    unittest.main()
