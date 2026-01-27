library BreastCancerScreening version '1.0.0'

/*
HEDIS Breast Cancer Screening (BCS) Digital Quality Measure
Measure Description: Percentage of women 50-74 years of age who had at least 
one mammogram to screen for breast cancer in the 27 months prior to the end 
of the measurement period.

Measurement Period: 27 months (current date - 27 months to current date)
*/

using FHIR version '4.0.1'

include FHIRHelpers version '4.0.1'

codesystem "CPT": 'http://www.ama-assn.org/go/cpt'
codesystem "ICD10": 'http://hl7.org/fhir/sid/icd-10-cm'

// Mammography CPT Codes
valueset "Mammography": {
  Code '77065' from "CPT" display 'Diagnostic mammography, including CAD; unilateral',
  Code '77066' from "CPT" display 'Diagnostic mammography bilateral, including CAD',
  Code '77067' from "CPT" display 'Screening mammography bilateral, including CAD',
  Code '77063' from "CPT" display 'Screening digital breast tomosynthesis, bilateral',
  Code '77061' from "CPT" display 'Digital breast tomosynthesis; unilateral',
  Code '77062' from "CPT" display 'Digital breast tomosynthesis; bilateral'
}

// Exclusion diagnoses - bilateral mastectomy
valueset "Bilateral Mastectomy": {
  Code 'Z90.13' from "ICD10" display 'Acquired absence of bilateral breasts and nipples'
}

// Unilateral mastectomy
valueset "Unilateral Mastectomy": {
  Code 'Z90.11' from "ICD10" display 'Acquired absence of right breast and nipple',
  Code 'Z90.12' from "ICD10" display 'Acquired absence of left breast and nipple'
}

parameter "Measurement Period" Interval<DateTime> default Interval[@2023-07-01T00:00:00.0, @2026-01-26T23:59:59.0]

context Patient

// Calculate patient age at end of measurement period
define "Patient Age":
  AgeInYearsAt(end of "Measurement Period")

// Initial Population: Female patients aged 50-74 at end of measurement period
define "Initial Population":
  Patient.gender = 'female'
    and "Patient Age" >= 50
    and "Patient Age" <= 74

// Denominator: Same as initial population
define "Denominator":
  "Initial Population"

// Exclusions: Bilateral mastectomy or two unilateral mastectomies
define "Bilateral Mastectomy Diagnosis":
  [Condition: "Bilateral Mastectomy"] BilateralMastectomy
    where BilateralMastectomy.clinicalStatus ~ ToConcept(Code 'active' from "http://terminology.hl7.org/CodeSystem/condition-clinical")

define "Unilateral Mastectomy Diagnoses":
  [Condition: "Unilateral Mastectomy"] UnilateralMastectomy
    where UnilateralMastectomy.clinicalStatus ~ ToConcept(Code 'active' from "http://terminology.hl7.org/CodeSystem/condition-clinical")

define "Has Bilateral Mastectomy Exclusion":
  exists "Bilateral Mastectomy Diagnosis"
    or Count("Unilateral Mastectomy Diagnoses") >= 2

define "Denominator Exclusions":
  "Has Bilateral Mastectomy Exclusion"

// Numerator: Patients who had at least one mammogram during measurement period
define "Mammography Claims":
  [Claim] MammoClaim
    where exists (
      MammoClaim.item ClaimItem
        where exists (
          ClaimItem.productOrService.coding Coding
            where Coding.code in "Mammography"
              and MammoClaim.created during "Measurement Period"
        )
    )

define "Has Qualifying Mammogram":
  Count("Mammography Claims") >= 1

define "Numerator":
  "Has Qualifying Mammogram"

// Final measure calculation
define "In Denominator":
  "Denominator" and not "Denominator Exclusions"

define "In Numerator":
  "In Denominator" and "Numerator"

// Gap in Care (patients who need screening)
define "Gap in Care":
  "In Denominator" and not "Numerator"
