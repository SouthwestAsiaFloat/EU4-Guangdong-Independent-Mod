"""Execute authored payment/transaction scripts in the existing scope model.

EU4 runtime and modifier rendering are deliberately not simulated here.
"""
from decimal import Decimal
import re
import unittest

from test_gdd_tianxia_buttons import ButtonWorld, MOD, entries


class AuthorityPayments(unittest.TestCase):
    def world(self, amount, actor=None):
        w = ButtonWorld()
        value = Decimal(str(amount))
        w.actor(actor or ("CZH" if value >= 0 else "YAN"))
        w.targets["gdd_principal_vassal"] = w.countries["YAN"]
        w.countries["CZH"].variables.update(
            gdd_central_authority_balance=value,
            gdd_authority_integer_display=value,
        )
        # Political-vote prerequisites are fixture inputs. The actual selected
        # guard, authorization, payment, flags and revalidation still execute.
        w.triggers["gdd_can_enact_proxy_keju_trigger"] = [("always", "yes")]
        for name in ("gdd_refresh_authority_balance_effects",
                     "gdd_clear_passed_reform_support_effect",
                     "gdd_recalculate_all_reform_votes_effect"):
            w.effects[name] = []
        return w

    def run_effect(self, w, name, key="gdd_proxy_reform_keju"):
        w.execute(w.effects[name], [w.root], {"which": key})

    def balance(self, w):
        return w.countries["CZH"].variables["gdd_central_authority_balance"]

    def test_exact_cost_and_fractional_boundaries_both_sides(self):
        for amount, expected, passed in (
            ("59.9", "59.9", False), ("60", "0", True),
            ("60.1", "0.1", True), ("100", "40", True),
            ("-59.9", "-59.9", False), ("-60", "0", True),
            ("-60.1", "-0.1", True), ("-100", "-40", True),
        ):
            with self.subTest(amount=amount):
                w = self.world(amount)
                self.run_effect(w, "gdd_enact_proxy_celestial_reform_effect")
                self.assertEqual(self.balance(w), Decimal(expected))
                self.assertEqual("gdd_proxy_reform_keju" in w.global_flags, passed)
                self.assertEqual(w.countries["CZH"].mandate, 50)
                self.assertEqual(w.root.stability, 0)

    def test_wrong_office_or_outsider_cannot_spend_other_side(self):
        for amount, actor in ((100, "YAN"), (-100, "CZH"), (100, "KRC")):
            w = self.world(amount, actor)
            self.run_effect(w, "gdd_enact_proxy_celestial_reform_effect")
            self.assertEqual(self.balance(w), amount)
            self.assertNotIn("gdd_proxy_reform_keju", w.global_flags)

    def test_stale_vote_rechecked_before_payment(self):
        w = self.world(100)
        w.triggers["gdd_can_enact_proxy_keju_trigger"] = [("always", "no")]
        self.run_effect(w, "gdd_enact_proxy_celestial_reform_effect")
        self.assertEqual(self.balance(w), 100)
        self.assertNotIn("gdd_proxy_reform_keju", w.global_flags)

    def test_duplicate_or_second_reform_cannot_spend_remaining_40(self):
        w = self.world(100)
        self.run_effect(w, "gdd_enact_proxy_celestial_reform_effect")
        self.run_effect(w, "gdd_enact_proxy_celestial_reform_effect")
        self.assertEqual(self.balance(w), 40)
        self.assertIn("gdd_proxy_reform_keju", w.global_flags)
        self.assertFalse(w.test("gdd_proxy_celestial_reform_base_trigger", w.root))

    def test_repeal_pays_once_without_support_and_keeps_backlash(self):
        for amount in (100, -100):
            w = self.world(amount)
            w.global_flags.add("gdd_proxy_reform_keju")
            w.countries["LUU"].flags["gdd_proxy_reform_keju"] = 0
            w.triggers["gdd_can_enact_proxy_keju_trigger"] = [("always", "no")]
            self.run_effect(w, "gdd_actively_revoke_proxy_celestial_reform_effect")
            self.assertEqual(self.balance(w), 40 if amount > 0 else -40)
            self.assertNotIn("gdd_proxy_reform_keju", w.global_flags)
            self.assertIn((w.root.tag, "gdd_opinion_revoked_tianxia_reform"),
                          w.countries["LUU"].opinions)
            self.run_effect(w, "gdd_actively_revoke_proxy_celestial_reform_effect")
            self.assertEqual(self.balance(w), 40 if amount > 0 else -40)

    def test_stale_repeal_with_insufficient_balance_preserves_reform(self):
        w = self.world(59.9)
        w.global_flags.add("gdd_proxy_reform_keju")
        self.run_effect(w, "gdd_actively_revoke_proxy_celestial_reform_effect")
        self.assertEqual(self.balance(w), Decimal("59.9"))
        self.assertIn("gdd_proxy_reform_keju", w.global_flags)

    def test_all_confirmation_events_use_paid_transaction_including_finales(self):
        events = [(k,v) for k,v in entries(MOD / "events/gdd_celestial_reform_revoke_events.txt") if k == "country_event"]
        self.assertEqual(len(events), 20)
        for kind, body in events:
            self.assertEqual(kind, "country_event")
            text = repr(body)
            self.assertIn("gdd_actively_revoke_proxy_celestial_reform_effect", text)
            self.assertNotIn("gdd_revoke_proxy_celestial_final_", text)

    def test_parameter_guards_exist_for_every_enactment_call(self):
        w = self.world(100)
        for path in [MOD / "events/gdd_celestial_test_events.txt",
                     MOD / "common/custom_gui/gdd_celestial_vassal_shields.txt"]:
            text = path.read_text()
            for key in re.findall(r"gdd_enact_proxy_celestial_reform_effect\s*=\s*\{\s*which\s*=\s*(\w+)", text):
                self.assertIn(key + "_can_enact", w.triggers)
                self.assertIn(key + "_on_pass", w.effects)
                self.assertIn(key + "_on_revoke", w.effects)


if __name__ == "__main__":
    unittest.main()
