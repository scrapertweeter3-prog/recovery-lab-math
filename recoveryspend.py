#!/usr/bin/env python3
"""recoveryspend: home recovery purchase vs drop-in price, per session.

Costs a home sauna / cold plunge / red-light panel against a studio drop-in
using nameplate energy math, per-session supplies, and amortized hardware,
then reports payoff time at your weekly frequency.

Stdlib only. Python 3.8+. No network.
"""
import argparse
import json
import sys

AMORT_SESSIONS_DEFAULT = 500  # sessions before hardware is considered paid off


def money(x):
    return round(x + 1e-9, 2)


def cost_model(price, watts, hours, preheat_frac, kwh, supplies_year,
               sessions_year, life_sessions):
    kw = watts / 1000.0
    energy = money(kw * (hours + preheat_frac) * kwh)
    supplies = money(supplies_year / sessions_year)
    marginal = money(energy + supplies)
    amortized = money(price / max(life_sessions, 1))
    allin = money(marginal + amortized)
    return {
        "kw": round(kw, 2),
        "hours_incl_preheat": round(hours + preheat_frac, 2),
        "kwh_rate": kwh,
        "energy_per_session": energy,
        "supplies_per_session": supplies,
        "marginal_per_session": marginal,
        "amortized_per_session": amortized,
        "allin_per_session": allin,
    }


def payoff(price, marginal, dropin, freq, life_sessions):
    """Weeks/years to pay off the purchase at `freq` sessions per week.

    Returns (weeks, years, note). weeks is None when it never pays off.
    """
    gap = dropin - marginal
    if dropin <= 0:
        return None, None, "gym is free (membership includes it): home never wins"
    if gap <= 0:
        return None, None, "energy+supplies already exceed the drop-in price"
    weeks = price / (gap * freq)
    return round(weeks, 1), round(weeks / 52.0, 1), None


def verdict_for(m, dropin, freq, life_sessions):
    """Honest verdict: does the purchase pay off inside the amortization
    window? That happens iff dropin >= marginal + amortized (the all-in)."""
    if dropin <= 0:
        return "keep the membership: the amenity is already free", 0
    if m["marginal_per_session"] >= dropin:
        return "home loses: running cost alone exceeds the drop-in", 1
    if m["allin_per_session"] <= dropin:
        return "home wins", 0
    return ("never amortizes in %d sessions: ownership play only"
            % life_sessions), 0


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Home recovery purchase vs drop-in: cost per session "
                    "and payoff time.")
    p.add_argument("--price", type=float, required=True,
                   help="purchase price of the home unit ($)")
    p.add_argument("--watts", type=float, required=True,
                   help="nameplate heater draw (W)")
    p.add_argument("--hours", type=float, default=0.75,
                   help="session length in hours (default 0.75)")
    p.add_argument("--preheat", type=float, default=0.5,
                   help="preheat draw in full-draw hours (default 0.5)")
    p.add_argument("--kwh", type=float, required=True,
                   help="your electric rate ($/kWh)")
    p.add_argument("--supplies-year", type=float, default=0.0,
                   help="annual filter/treatment cost ($)")
    p.add_argument("--sessions-year", type=int, default=100,
                   help="expected sessions per year (supplies divisor)")
    p.add_argument("--life-sessions", type=int,
                   default=AMORT_SESSIONS_DEFAULT,
                   help="sessions over which to amortize the purchase")
    p.add_argument("--dropin", type=float, required=True,
                   help="studio/gym drop-in price per session ($)")
    p.add_argument("--freq", type=float, default=1.0,
                   help="planned sessions per week for the payoff clock "
                        "(default 1.0)")
    p.add_argument("--name", default="home unit", help="label for output")
    p.add_argument("--json", action="store_true", help="JSON output")
    args = p.parse_args(argv)

    if args.sessions_year <= 0:
        p.error("--sessions-year must be positive")
    if args.life_sessions <= 0:
        p.error("--life-sessions must be positive")
    if args.freq <= 0:
        p.error("--freq must be positive")

    m = cost_model(args.price, args.watts, args.hours, args.preheat,
                   args.kwh, args.supplies_year, args.sessions_year,
                   args.life_sessions)
    weeks, years, note = payoff(args.price, m["marginal_per_session"],
                                args.dropin, args.freq, args.life_sessions)
    verdict, rc = verdict_for(m, args.dropin, args.freq, args.life_sessions)

    out = {
        "name": args.name,
        "dropin": args.dropin,
        "freq_per_week": args.freq,
        **m,
        "payoff_weeks_at_freq": weeks,
        "payoff_years_at_freq": years,
        "note": note,
        "verdict": verdict,
    }

    if args.json:
        print(json.dumps(out, indent=2))
        return rc

    print("== %s vs drop-in" % args.name)
    print("Energy per session     %6.2f  (%.2f kW, %.2f h incl. preheat, "
          "$%.3f/kWh)" % (m["energy_per_session"], m["kw"],
                          m["hours_incl_preheat"], args.kwh))
    print("Supplies per session   %6.2f  ($%.0f/yr, %d sessions/yr)"
          % (m["supplies_per_session"], args.supplies_year,
             args.sessions_year))
    print("Marginal cost/session  %6.2f" % m["marginal_per_session"])
    print("Amortized/session      %6.2f  (over %d sessions)"
          % (m["amortized_per_session"], args.life_sessions))
    print("All-in/session         %6.2f" % m["allin_per_session"])
    print("Drop-in price          %6.2f" % args.dropin)
    if note:
        print("Payoff                 %s" % note)
    else:
        print("Payoff at %.1f/wk     %6.1f wk  (%.1f yr)"
              % (args.freq, weeks, years))
    print("Verdict: %s" % verdict)
    return rc


if __name__ == "__main__":
    sys.exit(main())
