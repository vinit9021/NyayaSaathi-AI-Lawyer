# Source verification log — 9 November 2026

Method: browser research tool opened official pages and exposed their content.
Search-result snippets alone were not accepted. No private cases, provider keys,
or assignment PDFs were used. No PDF binaries were committed. The notes below
record actual successes and failures, not an assertion of exhaustive legal review.

## Active records

- `nch_grievance`: [NCH home](https://consumerhelpline.gov.in/public/) opened;
  read “How NCH Works.” Only grievance routing/tracking approved.
- `nch_online`: [NCH Consumer Protection Act FAQ](https://consumerhelpline.gov.in/public/knowledgebasedetails/Consumer%20Protection%20Act%202019)
  opened; questions 3–4 read. Only limited online-coverage guidance approved.
  The remainder of the FAQ is not imported as current legal guidance.
- `nalsa_help`: [NALSA legal aid](https://nalsa.gov.in/legal-aid/) opened via the
  official homepage's Legal Aid link. Reviewed eligibility and “Claiming Free
  Legal Aid / Application Procedure,” question 1. No income thresholds imported.
- `pib_model_tenancy`: [PIB release 1723636](https://www.pib.gov.in/PressReleasePage.aspx?PRID=1723636&reg=48&lang=2)
  opened after redirect. Read the opening policy announcement; no state adoption
  or statutory applicability conclusion inferred.

## Verified research material excluded from claim output

- [Department's Acts/Rules index](https://consumeraffairs.gov.in/pages/consumer-protection-acts)
  opened. Followed official download links for original rules and amendments.
- `ecommerce_original`: [Original 2020 rules](https://consumeraffairs.gov.in/public/upload/files/E%20commerce%20rules_1732703966.pdf)
  opened as an 11-page PDF; inspected extracted English rule 6(3) on printed
  page 10 and rule 4 on printed pages 8–9. Kept reference-only because document
  verification alone is not a consolidated current-law/applicability review.
- [2020 corrigendum](https://consumeraffairs.gov.in/public/upload/files/Corrigendum%20to%20e%20commerce%20rules_1732704181.pdf)
  opened and read; addresses clause lettering in the original publication.
- [2021 amendment](https://consumeraffairs.gov.in/public/upload/files/Consumer%20Protection%20(E-Commerce)%20(Amendment)%20Rules,%202021_1732704241.pdf)
  opened and read; concerns rule 4(1).
- [2026 amendment](https://consumeraffairs.gov.in/public/upload/files/E%20Commerce%20Amendment%20Rules%202026_1789127949.pdf)
  opened. Extracted text omits some numbers/dates. A screenshot request was made,
  but no usable image was available in the tool output for visual confirmation.
  No commencement date or amended obligation is approved on that basis.
  These supporting research documents are not separate active catalogue records.

## Unverified/failed attempts

- `indiacode_candidate`: [India Code PDF](https://www.indiacode.nic.in/bitstream/123456789/15256/1/eng201935.pdf)
  and [Act record](https://www.indiacode.nic.in/indiacode/handle/123456789/15256?sam_handle=123456789%2F1362&view_type=browse)
  timed out. No legal text was imported from the snippets.
- `tn_tenancy_candidate`: [Tamil Nadu official Act PDF](https://www.tenancy.tn.gov.in/Content/Documents/TNRRRLTact2017.pdf)
  returned 502 Bad Gateway; [portal](https://www.tenancy.tn.gov.in/) timed out.
  No rental cap, refund period, or section was approved.
- [Earlier NALSA path](https://nalsa.gov.in/services/legal-aid/) timed out.
  The separate `/legal-aid/` page above succeeded and is the catalogue URL.
- [PIB iframe path](https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=1723636&lang=2&reg=48)
  returned a cache miss. The standard release page above succeeded.

## Maintenance

Recheck source text and applicability before public release. A checked date is
not a guarantee that sources have not changed. The code uses a conservative
90-day review window; changing this policy requires documentation and tests.
English/Hindi claim wording is authored paraphrase, not verbatim statutory text.
No lawyer has independently validated this prototype catalogue in this task.
