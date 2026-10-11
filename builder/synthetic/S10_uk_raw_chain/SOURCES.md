# S10_uk_raw_chain - sources

Pennine & Wharfe Bank plc, its people and its e-mail domain (`pennine-wharfe.example`) are fictional.
The rules are built from real public UK texts. FCA Handbook text is paraphrased; only rule numbers and short
phrases are reused. UK legislation and gov.uk guidance are Crown copyright under the Open Government Licence.

| # | Real source | URL | Used in | How |
|---|---|---|---|---|
| 1 | FCA Handbook CONC 7.3.4R / 7.3.4B - treat customers in or approaching arrears with forbearance and due consideration; consider individual circumstances | https://www.handbook.fca.org.uk/handbook/CONC/7/3.html | policy 5.1 | paraphrase |
| 2 | CONC 7.3.5G - forbearance examples (suspending interest/charges, reduced payments, repayment arrangements) | same | policy 5.11.7 (only the Customer Support Unit agrees forbearance), e-mail [RP] 1 | paraphrase |
| 3 | CONC 7.3.10R - must not pressurise a customer to pay in one or very few repayments, in an unreasonably short period, or by borrowing / selling property | same | policy 5.10.4; memo 14 item 4 (justification for one Band 3 attempt) | paraphrase |
| 4 | CONC 7.3.11R / 7.3.12G - suspend active pursuit of recovery while a repayment plan is being developed; generally 30 days | same | memo 11 item 3 (debt advice hold, code DAH) | paraphrase, 30 days reused |
| 5 | CONC 7.3.7AG - refer customers to free, impartial debt advice | same | memo 11 item 3 list of providers | background |
| 6 | CONC 7.9.4R - must not contact customers at unreasonable times | https://www.handbook.fca.org.uk/handbook/CONC/7/9.html | policy 5.4.2 (callback window) | rule reused; hours invented (CONC gives none) |
| 7 | CONC 7.9.6R / 7.9.10R - no unfair disclosure to third parties; no disclosure until the person is established to be the borrower | same | policy 5.4.1, e-mail [RP] 2 (LPA proposal rejected), csv TPP retired | paraphrase |
| 8 | The Debt Respite Scheme (Breathing Space Moratorium and Mental Health Crisis Moratorium) (England and Wales) Regulations 2020, SI 2020/1311, reg. 7 - creditor must not take enforcement action / contact the debtor to enforce a moratorium debt | https://www.legislation.gov.uk/uksi/2020/1311/regulation/7/made | policy 5.10.3 | paraphrase |
| 9 | gov.uk, *Debt Respite Scheme (Breathing Space) guidance for creditors* - standard breathing space up to 60 days; mental health crisis breathing space lasts for the crisis treatment + 30 days; creditors must stop contact requesting payment; scheme in force 4 May 2021 | https://www.gov.uk/government/publications/debt-respite-scheme-breathing-space-guidance/debt-respite-scheme-breathing-space-guidance-for-creditors | e-mail [RP] 4 (both kinds treated alike), csv BRS valid_from 04/05/2021 | paraphrase / date |
| 10 | FCA FG21/1, *Guidance for firms on the fair treatment of vulnerable customers* - four drivers: health, life events, resilience, capability | https://www.fca.org.uk/publications/finalised-guidance/guidance-firms-fair-treatment-vulnerable-customers | policy 5.10.2 (vulnerability transfer, code XSV) | driver names reused |
| 11 | gov.uk bank holidays (JSON feed) - England and Wales: 25/12/2026, 28/12/2026 (Boxing Day substitute), 01/01/2027; Scotland adds 30/11/2026 St Andrew's Day and 04/01/2027 | https://www.gov.uk/bank-holidays.json | policy 5.7.1 Appendix A | dates reused exactly |
| 12 | Lending Standards Board, *Standards of Lending Practice for personal customers* (financial difficulty, consumer vulnerability) | https://lendingstandardsboard.org.uk/?p=6275 | policy structure (financial difficulty vs vulnerability split) | background only |
| 13 | StepChange / Citizens Advice / National Debtline / Christians Against Poverty - free UK debt advice providers; debt management plans | https://www.stepchange.org/ , https://www.nationaldebtline.org/ | memo 11 item 3, S10-07 script | names only |
| 14 | Collections disposition codes in practice (PTP, RTP, RPC, third-party / message codes) | https://www.virtualpbx.com/blog/contact-centers/list-of-call-disposition-codes-by-industry/ | csv layout (3-letter result codes, status, valid_from/valid_to) | style only |

Invented (needed to make the material executable with the 7 tools): the bands, limits, attempts and floors;
the two memos and their dates (migration closure 20/11 -> 27/11, Band 2 6th-BD pilot and its withdrawal,
Band 3 single attempt, Financial Support team); the e-mail thread and its people; the fixed sentences; all
result codes and queue names; the 12-pound late fee.
