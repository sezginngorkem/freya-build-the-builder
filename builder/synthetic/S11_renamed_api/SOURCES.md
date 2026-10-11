# S11_renamed_api - sources

Cascade Member Services LLC, Willamette Valley Credit Union, "Avery" and every customer are fictional.
The conduct rules are built from real public US federal law. Text is paraphrased; only section numbers and short
phrases are reused. Hours, bands, deadlines, codes and fixed sentences are invented for the test.

| # | Real source | URL | Used in | How |
|---|---|---|---|---|
| 1 | FDCPA 807(11), 15 U.S.C. 1692e(11): first communication must disclose that the collector is attempting to collect a debt and that information obtained will be used for that purpose | https://www.ftc.gov/legal-library/browse/rules/fair-debt-collection-practices-act-text | rule 25 (mini-Miranda sentence) | paraphrased into a fixed sentence |
| 2 | FDCPA 804, 15 U.S.C. 1692b: when contacting a third party, identify yourself, do not state that the consumer owes a debt | same | rules 1, 2, 5, 8-10 | paraphrase |
| 3 | FDCPA 805(b), 15 U.S.C. 1692c(b): no communication about the debt with third parties without consent | same | rules 2, 8, 9 | paraphrase |
| 4 | FDCPA 805(a)(1): no contact at a time known to be inconvenient; 805(a)(2): if represented by an attorney, deal with the attorney | same | rule 63 (RESCHED), rule 60 (ATY) | paraphrase |
| 5 | FDCPA 805(c), 15 U.S.C. 1692c(c): the consumer may require the collector to cease communication | same | rule 62 (CEASE); the brief makes it verbal and separates it from "I won't pay" | adapted |
| 6 | FDCPA 809, 15 U.S.C. 1692g: validation notice; a disputed debt is not collected until verification is mailed | same | rule 57 (DSP sentence) | paraphrase |
| 7 | FDCPA 807(4),(5): no threat of arrest, garnishment, seizure, or action not intended | same | rule 48 | paraphrase |
| 8 | Regulation F, 12 CFR 1006.14(b)(2): call-frequency presumption (7 calls in 7 days); 1006.14(h): no contact through a medium the person asked not to use ("stop calling" bars calls) | https://www.consumerfinance.gov/rules-policy/regulations/1006/14/ | rule 62 | background |
| 9 | Regulation F, 12 CFR 1006.6(b)(1): before 8 a.m. and after 9 p.m. local time presumed inconvenient | https://www.consumerfinance.gov/rules-policy/regulations/1006/6/ | rule 11 (callback window 09:00-20:00 lies inside it) | rule reused, hours narrowed |
| 10 | US federal holidays 2026 (Columbus / Indigenous Peoples' Day = 2nd Monday of October; Thanksgiving = 4th Thursday of November) | https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/ | calendar: 2026-10-12, 2026-11-26; 2026-11-27 is a Cascade closure; Veterans Day 2026-11-11 deliberately left a business day | dates computed |

Sources 1-8 were fetched on 2026-10-11; 9 and 10 are cited from general knowledge (not re-fetched).

Purpose of the suite: the only suite whose `openapi.json` renames the tool fields and enum values while keeping
the practice tool names, paths and server URL. See ANSWER_KEY.md for the mapping.
