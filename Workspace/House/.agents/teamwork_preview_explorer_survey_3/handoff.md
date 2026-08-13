# Handoff Report — Legal, Tax, Mortgage & Administrative Specifications

**Agent Identity**: teamwork_preview_spec_miner_3  
**Working Directory**: `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_3`  
**Target Specification Document**: `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_3/survey_legal_mortgage.md`

---

## 1. Observation
- Read `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md` (lines 1-57), which specifies the target property (Cheongju Bangseo-dong Xi <30 pyeong, 3.5억/3.75억/4억 KRW scenarios, married joint ownership, second-hand move-in) and requires full survey of one-time costs (acquisition tax, legal fees, broker fees, stamp duty, housing bonds, moving/cleaning), loan scenarios (Didimdol/Bogeumjari vs Commercial Banks + secondary loan fees), and administrative checklist.
- Read `/home/imnyj/Workspace/House/data/정보.md` (lines 1-38), establishing buyer context: Nam Young-ju (education public servant, net monthly income 3.3M KRW, total annual ~70M KRW) and Kim Eun-bi (self-employed restaurant owner), newlywed joint ownership, 2.3억 KRW initial cash (30M own + 200M parents).
- Investigated 2025-2026 Korean tax laws (Local Tax Act Article 11, Local Tax Exemption Limitation Act Article 36-2 for first-time homebuyers), Licensed Real Estate Agents Act Implementation Rule (broker fee cap 0.4%), Stamp Duty Act Article 3, Housing Law Enforcement Decree Table 12 (National Housing Bond discount calculation), Korean Housing Finance Corporation (HF) Didimdol / Bogeumjari rules, and Cheongju local administrative procedures.

## 2. Logic Chain
1. **One-Time Cost Calculation**:
   - For Exclusive Area < 30 pyeong (≤ 85㎡) in non-regulated Cheongju:
     - Acquisition Tax base rate = 1.0% + Local Edu Tax 0.1% = 1.1%. (Rural Special Tax = 0% for ≤ 85㎡).
     - First-time Homebuyer Exemption under Local Tax Exemption Limitation Act Art. 36-2 provides up to 2,000,000 KRW reduction (no income limit for first-time 1-house buyers up to 12억 KRW house price).
     - Applied net acquisition taxes: 3.5억 → 1.65M KRW, 3.75억 → 1.925M KRW, 4.0억 → 2.2M KRW.
   - Brokerage Fee: Statutory upper limit is 0.4% for 2억~9억 KRW residential sale + 10% VAT (0.44%). Applied fees: 3.5억 → 1.54M KRW, 3.75억 → 1.65M KRW, 4.0억 → 1.76M KRW.
   - Judicial Scrivener Fee: Estimated at 500K / 520K / 550K KRW based on Certified Judicial Scrivener Association standards.
   - Stamp Duty: 150,000 KRW flat rate for real estate transfer >100M & ≤1,000M KRW.
   - National Housing Bond Discount: Official assessed value (~70% of price) × bond purchase rate (2.1%~2.3%) × discount rate (~10%). Net out-of-pocket: 3.5억 → 515K KRW, 3.75억 → 604K KRW, 4.0억 → 644K KRW.
   - Moving & Cleaning/Repair: Packaging move (1.5M KRW) + Deep cleaning & basic repair (2.0M KRW) = 3.5M KRW total.
   - **Total One-Time Costs**: 3.5억 → 7.855M KRW, 3.75억 → 8.349M KRW, 4.0억 → 8.804M KRW.

2. **Mortgage Scenario & Secondary Fees Analysis**:
   - Initial cash on hand: 2.3억 KRW. Required loan amounts: 3.5억 → 1.2억 KRW (LTV 34.3%), 3.75억 → 1.45억 KRW (LTV 38.7%), 4.0억 → 1.7억 KRW (LTV 42.5%).
   - Didimdol Loan (Newlywed rate): Income cap 85M KRW, House price ≤6억 KRW, Size ≤85㎡. Interest rate 3.0%~3.3%, max limit 4.0억 KRW. Optimal 1st priority choice.
   - Bogeumjari Loan: Fixed rate 3.8%~4.1%, max limit 4.2억 KRW. 2nd priority fixed-rate alternative.
   - Commercial Bank Loan: Rate 3.9%~4.6%, DSR 40% cap. 3rd priority alternative if income cap exceeded.
   - Secondary Fees: Mortgage setup fee (Bank 100% pays registration tax and legal fee; borrower pays ~10K~30K KRW registry fee), Loan stamp tax (150K KRW split 50:50 → borrower pays 75,000 KRW), HF Guarantee Fee (~60K~170K KRW/year).

3. **Administrative Reporting Checklist**:
   - Timeline: (1) Transaction Price Report within 30 days of contract → (2) Balance Payment & Key Handover on contract date → (3) Acquisition Tax Declaration & Payment within 60 days (before registration) → (4) Ownership Transfer Registration within 60 days (on balance day) → (5) Moving-in Report within 14 days → (6) Property Tax & Comprehensive Real Estate Tax (Tax base date June 1st; Property tax in July/Sept; 종부세 0 KRW exempt due to 12억/18억 KRW threshold).

## 3. Caveats
- **Bond Discount Rate**: National Housing Bond discount rates fluctuate daily on the bond market (typically between 8% and 12%). A standard 10% rate was applied.
- **Assessed Official Price**: Official assessed values for Cheongju Bangseo-dong Xi were estimated at ~70% of market transaction price. Exact official value for specific building/unit should be checked on Hometax/Real Estate Public Price Portal when executing actual transaction.
- **Combined Income Eligibility**: If Kim Eun-bi's business income causes total combined income to exceed 85M KRW, Didimdol eligibility shifts to Bogeumjari or Commercial bank loans.

## 4. Conclusion
All legal, tax, mortgage, and administrative specifications for acquiring an apartment in Cheongju Bangseo-dong Xi (<30 pyeong, 3.5억/3.75억/4억) have been exhaustively surveyed, calculated, and documented at `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_3/survey_legal_mortgage.md`. The findings provide exact input parameters, formulas, and step-by-step checklists ready for financial simulation and HTML builder integration.

## 5. Verification Method
- Inspect document: `view_file` on `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_3/survey_legal_mortgage.md`.
- Verify formulas:
  - Acquisition Tax: `(Price * 0.01) - 2,000,000 + (Acquisition Tax * 0.1)`
  - Broker Fee: `Price * 0.004 * 1.1`
  - Stamp Duty: `150,000 KRW` for transfer, `75,000 KRW` for loan borrower share.
  - Required Loan: `Price - 2.3억 KRW`.
