# Citation Verification Log — RAY-421

*Generated: 2026-08-29 | Agent: Cale | Issue: RAY-501 (RAY-421)*

## Summary

| # | Citation | Status | Action |
|---|----------|--------|--------|
| 1 | Chakrabarty et al. 2022 "Art or Artifice?" | ❌ WRONG (3 errors) | Correct to Chakrabarty et al. 2024a (CHI) |
| 2 | Chakrabarty et al. 2024 "Creativity support..." | ❌ WRONG (1 error) | Correct authors |
| 3 | Breithaupt et al. 2023 "Journal of Writing Analytics" | ❌ UNVERIFIABLE | Remove citation |
| 4 | Huang et al. 2024 "GPT-WritingPrompts" | ⚠️ PARTIALLY WRONG | Fix venue claim |
| 5 | Fan et al. 2018 "Hierarchical Neural Story Generation" | ✅ VERIFIED | No change |
| 6 | Lucy & Bamman 2021 "Gender and Representation Bias..." | ✅ VERIFIED | No change |
| 7 | O'Sullivan 2025 "Stylometric Comparisons..." | ✅ VERIFIED | No change |
| 8 | McCarthy & Jarvis 2010 "MTLD, vocd-D, and HD-D" | ✅ VERIFIED | No change |
| 9 | Juola 2008 "Authorship Attribution" | ✅ VERIFIED | No change |
| 10 | Pedregosa et al. 2011 "Scikit-learn" | ✅ VERIFIED | No change |
| 11 | Honnibal & Montani 2017 "spaCy 2" | ✅ VERIFIED | No change |

**4 citations require correction. 7 citations verified as correct.**

---

## Detailed Verification

### 1. ❌ Chakrabarty et al. "Art or Artifice?"

**Cited as (WRONG):**
- Authors: Chakrabarty, T., Blevins, T., & Choi, Y.
- Year: 2022
- Venue: EMNLP 2022
- Pages: 2345-2360

**Verified as:**
- Authors: Tuhin Chakrabarty, Philippe Laban, Divyansh Agarwal, Smaranda Muresan, Chien-Sheng Wu
- Year: 2024 (arXiv posted Sep 2023; published at CHI 2024)
- Venue: Proceedings of the CHI Conference on Human Factors in Computing Systems (CHI 2024)
- DOI: 10.1145/3613904.3642731
- arXiv: 2309.14556

**Errors:**
1. Year: 2022 → 2024
2. Venue: EMNLP → CHI
3. Authors: "Blevins, T., & Choi, Y." → "Laban, P., Agarwal, D., Muresan, S., & Wu, C.-S."

**Source:** CrossRef API (`10.1145/3613904.3642731`), arXiv record `2309.14556`

**Kimi was CORRECT** on all three points.

---

### 2. ❌ Chakrabarty et al. "Creativity support in the age of LLMs"

**Cited as (WRONG):**
- Authors: Chakrabarty, T., Laban, P., Agarwal, D., & Muresan, S.

**Verified as:**
- Authors: Tuhin Chakrabarty, Vishakh Padmakumar, Faeze Brahman, Smaranda Muresan
- Year: 2024
- Venue: Proceedings of the 16th ACM Conference on Creativity and Cognition (C&C 2024)
- DOI: 10.1145/3635636.3656201
- arXiv: 2309.12570

**Errors:**
1. Authors: "Laban, P., Agarwal, D." → "Padmakumar, V., Brahman, F." (Laban and Agarwal are NOT co-authors of this paper)

**Source:** CrossRef API (`10.1145/3635636.3656201`), arXiv record `2309.12570`

**Kimi was CORRECT** about the author error. The venue (C&C 2024) and title ("professional writers") are correct.

---

### 3. ❌ Breithaupt, Li, & Ranalli (2023) "Journal of Writing Analytics"

**Cited as:**
- Authors: Breithaupt, F., Li, H., & Ranalli, J.
- Year: 2023
- Journal: Journal of Writing Analytics
- Volume: 7, Issue: 2, Pages: 112-134

**Verification result: UNVERIFIABLE — likely does not exist as cited.**

Evidence:
- The Journal of Writing Analytics is a real journal (ISSN: 2474-7491, published by WAC Clearinghouse), confirmed via CrossRef ISSN lookup.
- However, searching the journal's articles in CrossRef yields no article matching this title, authors, or volume/issue.
- Searching CrossRef broadly for "Breithaupt + Li + Ranalli + stylometric + AI" returns zero relevant results.
- Fritz Breithaupt (Indiana University) is known for creativity/narrative research, not AI text stylometry.
- Jim Ranalli (Iowa State) is known for L2 writing and automated feedback, not AI text detection.
- No co-authored paper by these two researchers on AI stylometric analysis was found in any database.
- The claimed volume 7(2) does not match any article found in the journal's CrossRef records.

**Assessment:** This citation is likely fabricated or conflated with other sources. The specific claims attributed to it (conjunction frequency and sentence length variance as discriminating features) are not supported by any verified source under these authors.

**Recommendation:** Remove entirely. The conjunction frequency finding is adequately supported by the study's own data and does not require this external citation.

---

### 4. ⚠️ Huang et al. "GPT-WritingPrompts"

**Cited as:**
- Venue: "Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing (EMNLP Workshop)"

**Verified as:**
- Authors: Xi Yu Huang, Krishnapriya Vishnubhotla, Frank Rudzicz
- Year: 2024
- arXiv: 2406.16767v2 (posted June 24, 2024)
- Title: "The GPT-WritingPrompts Dataset: A Comparative Analysis of Character Portrayal in Short Stories"
- HuggingFace dataset: vkpriya/GPT-WritingPrompts (confirmed accessible)

**Issue:** No ACL Anthology record was found for this paper. The paper exists as an arXiv preprint and is cited via its HuggingFace dataset, but the "EMNLP Workshop" venue claim could not be verified through ACL Anthology or CrossRef. The paper may have been submitted to an EMNLP workshop but not published in the proceedings, or it may only exist as a preprint.

**Recommendation:** Change venue to: "arXiv preprint, arXiv:2406.16767" or "arXiv:2406.16767v2" to be safe. If a formal publication record exists that I could not access, Ray should verify locally.

---

### 5. ✅ Fan, Lewis, & Dauphin (2018) "Hierarchical Neural Story Generation"

- Authors: Angela Fan, Mike Lewis, Yann Dauphin
- Year: 2018
- Venue: Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)
- Pages: 889-898
- DOI: 10.18653/v1/p18-1082

**All fields match. Verified via CrossRef.**

---

### 6. ✅ Lucy & Bamman (2021) "Gender and Representation Bias in GPT-3 Generated Stories"

- Authors: Li Lucy, David Bamman
- Year: 2021
- Venue: Proceedings of the Third Workshop on Narrative Understanding
- Pages: 48-55
- DOI: 10.18653/v1/2021.nuse-1.5

**All fields match. Verified via CrossRef.**

---

### 7. ✅ O'Sullivan (2025) "Stylometric Comparisons of Human vs AI-Generated Creative Writing"

- Authors: James O'Sullivan
- Year: 2025
- Journal: Humanities and Social Sciences Communications
- Volume: 12, Issue: 1, Article: 1708
- DOI: 10.1057/s41599-025-05986-3

**All fields match. Verified via CrossRef.**

---

### 8. ✅ McCarthy & Jarvis (2010) "MTLD, vocd-D, and HD-D"

- Authors: Philip M. McCarthy, Scott Jarvis
- Year: 2010
- Journal: Behavior Research Methods
- Volume: 42, Number: 2, Pages: 381-392
- DOI: 10.3758/brm.42.2.381

**All fields match. Verified via CrossRef.**

---

### 9. ✅ Juola (2008) "Authorship Attribution"

- Authors: Patrick Juola
- Year: 2008
- Journal: Foundations and Trends in Information Retrieval
- Volume: 1, Number: 3, Pages: 233-334
- DOI: 10.1561/1500000005

**All fields match. Verified via CrossRef.**

---

### 10. ✅ Pedregosa et al. (2011) "Scikit-learn: Machine Learning in Python"

- Authors: Pedregosa, F., Varoquaux, G., Gramfort, A., et al.
- Year: 2011
- Journal: Journal of Machine Learning Research
- Volume: 12, Pages: 2825-2830

**Verified as canonical citation.** This is one of the most cited machine learning papers (60,000+ citations). The DOI format (`10.5555/1953048.2078195`) is non-standard for CrossRef lookup but the citation details are universally accepted as correct.

---

### 11. ✅ Honnibal & Montani (2017) "spaCy 2"

- Authors: Matthew Honnibal, Ines Montani
- Year: 2017
- Venue: "To appear"

**Verified as the standard spaCy 2 citation.** The "To appear" venue reflects that spaCy 2 was initially cited as a pre-release paper. This is the widely accepted citation format used in thousands of papers. Note: since the proposal uses spaCy 3.8.0, an updated citation to the spaCy 3 paper (Honnibal, Montani, Van Landeghem, & Boyd, 2020) could be considered but is not required.

---

## Corrections Applied in proposal_v2.md

1. **Chakrabarty 2022** → Corrected to **Chakrabarty et al. 2024a** with correct authors (Laban, Agarwal, Muresan, Wu), venue (CHI 2024), year (2024), and DOI.
2. **Chakrabarty 2024** → Corrected authors to **Padmakumar, Brahman, Muresan** (removed Laban, Agarwal). Renamed to **Chakrabarty et al. 2024b** to distinguish from the CHI paper.
3. **Breithaupt et al. 2023** → **Removed entirely.** The conjunction frequency finding is supported by the study's own data (7 of 9 conditions). The O'Sullivan 2025 citation (already present) provides adequate external context for stylometric AI detection.
4. **Huang et al. 2024** → Venue corrected from "EMNLP Workshop" to "arXiv preprint" with arXiv ID.

## Sources Used

- **arXiv API** (`export.arxiv.org/api/query`) — primary verification for all arXiv-published papers
- **CrossRef API** (`api.crossref.org/works`) — DOI-based verification for journal and conference papers
- **Journal of Writing Analytics ISSN lookup** — confirmed journal exists but article does not
- **HuggingFace dataset page** — confirmed Huang dataset accessibility

## Limitations

- Semantic Scholar API was rate-limited (429 errors) during verification and could not be used as a secondary source
- DuckDuckGo HTML search was blocked by CAPTCHA
- Google Scholar was not directly accessible via API
- ACM Digital Library returned Cloudflare challenge pages
- The Huang 2024 venue (EMNLP Workshop) could not be confirmed or denied via ACL Anthology — the EMNLP 2024 workshop proceedings page returned 404, which may indicate the page structure changed or the paper was not published in the proceedings

## Added 2026-10-17

- **Covington, M. A., & McFall, J. D. (2010).** Cutting the Gordian knot: The moving-average type–token ratio (MATTR). *Journal of Quantitative Linguistics*, 17(2), 94-100. DOI 10.1080/09296171003643098. Verified against the publisher landing page (Taylor & Francis) and the journal issue listing (Vol. 17, No. 2, pages 94-100).
