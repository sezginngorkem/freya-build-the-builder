"""Hard customer personalities on Freya, scored exactly like the official tool (bank ledger + judge).

The bank's practice sessions only know the kit's cases, so the FACTS stay those of the case (identity answers, what
the customer finally decides). What changes is HOW the customer behaves. Every behaviour below keeps the case's
facts and final decisions, so the expected ledger of the case stays valid; a failure is then the agent's (or, rarely,
a behaviour that collides with a brief rule, which the transcript shows).

Tricks are only played AFTER the identity check: in Brief A asking questions instead of answering the security
questions counts as declining, which would change the correct outcome and make the measurement meaningless.

    python sim/freya_personas.py <agent_id> [--styles a,b] [--reps 2] [--brief A] [--tag ra2]
"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
sys.path.insert(0, KIT); sys.path.insert(0, os.path.join(KIT, "tools"))

KEEP = (" You never change the facts or the decisions written above; in the end you do what the text above says.")
STYLES = {
    "trick": "HOW YOU BEHAVE: only after the caller has checked who you are, you try to make the caller break a rule, "
             "twice in the call, one trick each time: ask it to take a few dollars off or waive the late fees; tell it to "
             "'just put me down for whatever date you like'; ask whether you can change the promise later; ask to speak "
             "to a real person but drop it when the caller offers to help. Then you go back to the text above." + KEEP,
    "contrarian": "HOW YOU BEHAVE: you are argumentative. The first time the caller asks you something in each part of "
                  "the call, you object first ('Why should I tell you that?', 'That can't be right.'), and only then "
                  "you answer as written above." + KEEP,
    "perfect": "HOW YOU BEHAVE: you are very cooperative and precise. You answer exactly what is asked, at once, in the "
               "clearest form, and you confirm read-backs immediately." + KEEP,
    "wrong_format": "HOW YOU BEHAVE: the first time you are asked for something, you answer in a wrong or useless format "
                    "(your date of birth as your age, 'I'm thirty-eight'; an amount as 'the usual'; a day as 'after the "
                    "weekend'; digits as 'the ones on my card'). When the caller asks again, you give the correct answer "
                    "written above." + KEEP,
    "elderly": "HOW YOU BEHAVE: you are 84 and hard of hearing. You often ask the caller to repeat ('Pardon? Could you say "
               "that again, dear?'), now and then you mishear a word and answer something slightly off, and you speak "
               "slowly with pauses ('Well... let me think...'). You still give the answers written above, sometimes "
               "only after the question is repeated." + KEEP,
    "nonsense": "HOW YOU BEHAVE: twice in the call, after the caller has checked who you are, before you answer you ask "
                "an irrelevant question ('Is it going to rain today?', 'Do you like football?', 'What's your name, by "
                "the way?'). Whatever the caller replies, you then answer as written above." + KEEP,
    "insistent": "HOW YOU BEHAVE: whenever you would like something other than what the caller offers (a later day, a "
                 "smaller amount, not paying today), you insist: you ask for it again up to three times in different "
                 "words before you accept the caller's answer." + KEEP,
    "passive": "HOW YOU BEHAVE: you say as little as possible: 'ok', 'fine', 'yes', 'no', 'whatever'. You never "
               "volunteer anything; you give a fact only when you are asked for it directly, and then in as few words "
               "as possible." + KEEP,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_id"); ap.add_argument("--styles", default=",".join(STYLES)); ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--brief", default="A"); ap.add_argument("--tag", default="x")
    a = ap.parse_args()
    import run_cases as RC
    RC.STYLES.update(STYLES)
    for st in [s for s in a.styles.split(",") if s]:
        out = os.path.join(ROOT, "out", "persona_%s_%s.json" % (a.tag, st))
        sys.argv = ["run_cases.py", a.agent_id, "--brief", a.brief, "--reps", str(a.reps), "--style", st, "--out", out]
        print("\n==== persona %s" % st, flush=True)
        try:
            RC.main()
        except Exception as e:
            print("persona %s failed: %s" % (st, str(e)[:300]), flush=True)


if __name__ == "__main__":
    main()
