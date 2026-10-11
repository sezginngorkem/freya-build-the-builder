# S7_unseen_real - sources

Cobalt Ridge Federal Credit Union, its people and its e-mail domain (`cobaltridge-fcu.example`) are fictional.
The rules are built from real public texts. US federal regulations (CFR) are public domain and are quoted
verbatim or near-verbatim. FCA Handbook and Fannie Mae text is paraphrased; only rule numbers, short phrases
and code names/numbers are reused.

| # | Real source | URL | Used in | How |
|---|---|---|---|---|
| 1 | Regulation F, 12 CFR 1006.6(d)(1) - communications with third parties | https://www.law.cornell.edu/cfr/text/12/1006.6 | policy 7.4.1 | verbatim quote of the (i)-(vi) list |
| 2 | Regulation F, 12 CFR 1006.6(b)(1) - inconvenient times (before 8:00 a.m., after 9:00 p.m.) | https://www.law.cornell.edu/cfr/text/12/1006.6 | policy 7.4.2 (base callback window); memo item 1 ("knows or should know is inconvenient") | verbatim phrase, turned into a callback window |
| 3 | Regulation F, 12 CFR 1006.6(b)(2) - consumer represented by an attorney | https://www.law.cornell.edu/cfr/text/12/1006.6 | policy 7.6.4, code ATY | paraphrase |
| 4 | Regulation F, 12 CFR 1006.18(e) - disclosure that the collector is attempting to collect a debt ("mini-Miranda") | https://www.law.cornell.edu/cfr/text/12/1006.18 | policy 7.6.2 fixed sentence | standard industry wording of the required disclosure |
| 5 | Regulation F, 12 CFR 1006.14(b) - 7-in-7 call frequency; 2021-11-30 effective date of Reg F | https://www.law.cornell.edu/cfr/text/12/1006.14 , https://www.consumerfinance.gov/rules-policy/regulations/1006/14/ | codes.csv (TPM retired on 2021-11-30; LVM limited-content message) | background / dates only |
| 6 | 34 CFR 682.411 - lender due diligence: delinquency bands (1-15 days, 16-180 days), delinquency starts "the day after the due date of the first missed payment" | https://www.law.cornell.edu/cfr/text/34/682.411 | policy 7.1 (delinquency definition), 7.7.2 (Stage 1 = 1-15 days) | definition near-verbatim; band boundary reused |
| 7 | Regulation X, 12 CFR 1024.39(a) - early intervention: live contact by the 36th day of delinquency and information about loss mitigation options | https://www.law.cornell.edu/cfr/text/12/1024.39 | memo item 3 (36+ days loans -> Loan Workout offer) | paraphrase, adapted from mortgages to consumer loans |
| 8 | FCA Handbook CONC 7.3.10R (no pressure to pay in one/very few repayments, unreasonably short period, or by borrowing/selling property) | https://www.handbook.fca.org.uk/handbook/CONC/7/3.html | policy 7.8.1 | paraphrase with short phrases |
| 9 | FCA Handbook CONC 7.3.11R / 7.3.12G (suspend recovery for a reasonable period, generally 30 days, while a debt counsellor develops a repayment plan) | https://www.handbook.fca.org.uk/handbook/CONC/7/3.html | memo item 2 (credit counselor -> 30-day hold) | paraphrase |
| 10 | Fannie Mae Servicing Guide F-1-21 - Reason for Delinquency codes (002, 003, 004, 005, 006, 016, 027, 031) | https://servicing-guide.fanniemae.com/svc/f-1-21/reporting-delinquent-mortgage-loan-fannie-maes-servicing-solutions-system | codes.csv rows with category DLQ_REASON; policy 7.12.1 | code numbers and short names |
| 11 | Federal Reserve holiday schedule 2026/2027 | https://www.federalreserve.gov/aboutthefed/k8.htm | policy 7.7.1 Appendix B | dates (Columbus Day 10/12, Veterans Day 11/11, Thanksgiving 11/26, Christmas 12/25, New Year 1/1, MLK 1/18/2027) |
| 12 | CUES sample "Consumer & Residential Loan Collections Policy" (credit-union policy template; purpose clause) | https://www.cues.org/sites/default/files/2017-08/726_Consumer%20&%20Residential%20Loan%20Collections%20Policy.doc | policy 7.1 first sentence ("most prudent and effective collection practices ... every effort to bring delinquent loans ... current") | near-verbatim purpose clause as quoted in search results (file itself returned 403) |
| 13 | Contact-centre disposition code lists (e.g. Vonage/NewVoiceMedia dispositions: Wrong Number, Set Callback, Left Voicemail, Transfer; LiveVox PTP termination codes) | https://docs-vcc.atlassian.net/wiki/x/_oHBJw , https://livevox.helpjuice.com/en_US/using-the-agent-desktop/using-termination-codes | codes.csv layout (3-letter result codes, ACTIVE/INACTIVE) | style only |

Invented (not from a real source, needed to make the brief executable with the 7 tools):
stage 2/3 boundaries (16-59, 60-120) and promise-date limits (10th/6th/3rd business day), persuasion
attempts, floors, the credit union's closure on 2026-11-27, the 09:00-20:00 / 2-business-day memo values,
the e-mail thread, fixed sentence in 7.10.4, codes PTP...NCU names.
