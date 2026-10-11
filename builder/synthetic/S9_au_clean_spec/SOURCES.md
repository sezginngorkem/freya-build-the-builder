# S9_au_clean_spec - sources

Kestrel Mutual Bank, its people and its customers are fictional. The rules are adapted from real public
Australian material. Code text is paraphrased; only short phrases, list items and dates are reused.

| # | Real source | URL | Used in | How |
|---|---|---|---|---|
| 1 | ACCC & ASIC, *Debt collection guideline: for collectors and creditors* (April 2021) - contact hours: phone Mon-Fri 7:30 am-9 pm, weekends 9 am-9 pm, no contact on national public holidays; frequency benchmark 3 calls/week, 10/month; no disclosure to third parties | https://www.accc.gov.au/system/files/Debt%20collection%20guideline%20for%20collectors%20and%20creditors%20-%20April%202021.pdf (403 to robots; hours confirmed via https://www.accc.gov.au/business/debt/debt-collection-rules and https://www.canstar.com.au/credit-score/debt-collection-guidelines/) | rule 8 (callback hours 07:30-21:00 weekdays, 09:00-21:00 weekends, no public holidays), rule 7 (third parties) | hours reused exactly; frequency not used (the agent cannot see call history) |
| 2 | Australian Banking Association, *Banking Code of Practice* (published 27 June 2024, in force 28 Feb 2025), para 52 - vulnerability characteristics: age, disability, mental health conditions, cognitive impairment, serious medical conditions, elder abuse, family and/or domestic violence, financial abuse, Financial Difficulty, language barriers ... | https://www.ing.com.au/pdf/Banking_Code_of_Practice.pdf (copy of the ABA text) | rule 38 (vulnerability trigger list, transfer to Customer Care) | subset of the list; "serious medical conditions" moved to hardship to keep the two rules disjoint |
| 3 | Banking Code of Practice para 168 - Financial Difficulty causes: illness or injury, loss of employment, pandemic, natural disasters | same | rule 39 (hardship triggers) | list reused |
| 4 | Banking Code of Practice paras 170-171 - customer may tell the bank to deal with their financial counsellor or representative | same | rule 41 (financial counsellor -> pause) | adapted to a phone rule |
| 5 | Banking Code of Practice para 182 - bank will not require the customer to access superannuation | same | rule 37 (never suggest superannuation, borrowing, selling) | paraphrase |
| 6 | Banking Code of Practice para 187 - banks comply with the ACCC/ASIC Debt Collection Guideline | same | header of brief | reference |
| 7 | Westpac hardship FAQ - "suspends collections activity for 21 days" while assessing a hardship situation | https://westpac.com.au/faq/financial-hardship | rule 41 / S-HOLD (21-day pause) | number reused; trigger adapted to "financial counsellor already helping" |
| 8 | Business Victoria, *Public holidays in Victoria 2026* - Melbourne Cup Tue 3 Nov 2026; Christmas Fri 25 Dec; Boxing Day Sat 26 Dec with substitute Mon 28 Dec | https://business.vic.gov.au/business-information/public-holidays/victorian-public-holidays-2026 | rule 17 | dates reused exactly; 2027-01-01 and 2027-01-26 from the standard national list |
| 9 | National Debt Helpline (free financial counselling, Australia) | https://ndh.org.au/ | S9-10 script | name only |
| 10 | Australia Post postcode conventions (NT postcodes start with 08, 4 digits) | https://auspost.com.au/postcode | rule 12, S9-01 ("0870" Alice Springs) | format |

Invented (needed to make the brief executable with the 7 tools): the three stages and their limits,
attempt counts, the Stage C 25% floor rule, the fixed sentences, the callback horizon (today + 2 calendar
days), the split-payment rule, the note/close tables, queue and reason names.
