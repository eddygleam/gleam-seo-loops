import unittest

from gleam_seo.classify import Track, classify, is_excluded, normalize


class TestNormalize(unittest.TestCase):
    def test_lowercase_and_collapse_whitespace(self):
        self.assertEqual(normalize("  Gleam   App  "), "gleam app")


class TestExclusions(unittest.TestCase):
    def test_exact_exclusions_dropped(self):
        for q in [
            "software giveaway",
            "software giveaways",
            "free software",
            "giveaway of the day",
            "steam key",
            "nft giveaway",
            "crypto giveaway",
        ]:
            self.assertTrue(is_excluded(q), q)
            self.assertIs(classify(q), Track.EXCLUDED, q)

    def test_exclusion_matches_as_substring(self):
        self.assertIs(classify("best steam key sites"), Track.EXCLUDED)

    def test_relevant_giveaway_not_excluded(self):
        self.assertIsNot(classify("instagram giveaway ideas"), Track.EXCLUDED)


class TestBrand(unittest.TestCase):
    def test_bare_gleam_is_brand(self):
        self.assertIs(classify("gleam"), Track.BRAND)

    def test_gleam_alternative_is_brand_not_conquest(self):
        self.assertIs(classify("gleam alternative"), Track.BRAND)

    def test_gleam_with_commercial_signal_is_still_brand(self):
        # Rule 2: anything containing "gleam" is brand, full stop.
        self.assertIs(classify("gleam tool"), Track.BRAND)
        self.assertIs(classify("gleam.io app"), Track.BRAND)

    def test_gleam_pricing_reviews_are_brand(self):
        self.assertIs(classify("gleam pricing"), Track.BRAND)
        self.assertIs(classify("gleam reviews"), Track.BRAND)


class TestCommercial(unittest.TestCase):
    def test_conquest_competitor_alternative(self):
        self.assertIs(classify("rafflecopter alternative"), Track.COMMERCIAL)

    def test_tool_words(self):
        for q in [
            "giveaway tool",
            "giveaway tools",
            "sweepstakes software",
            "contest platform",
            "instagram giveaway picker",
            "random name generator",
            "meme maker",
            "competition websites",
        ]:
            self.assertIs(classify(q), Track.COMMERCIAL, q)

    def test_action_phrasings(self):
        for q in ["run a giveaway", "host a contest", "create a competition"]:
            self.assertIs(classify(q), Track.COMMERCIAL, q)


class TestInformational(unittest.TestCase):
    def test_informational_words(self):
        for q in [
            "giveaway ideas",
            "contest examples",
            "how to run a raffle",
            "giveaway rules",
            "sweepstakes legal requirements",
        ]:
            self.assertIs(classify(q), Track.INFORMATIONAL, q)


class TestOther(unittest.TestCase):
    def test_unmatched_is_other(self):
        self.assertIs(classify("marketing"), Track.OTHER)


if __name__ == "__main__":
    unittest.main()
