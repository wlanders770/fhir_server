library HEDISColorectalCancerScreening version '1.0.0'

using FHIR version '4.0.1'

include FHIRHelpers version '4.0.1' called FHIRHelpers

context Patient

/*
 * HEDIS Colorectal Cancer Screening (COL) Measure
 * 
 * Description:
 * Percentage of adults 45-75 years of age who had appropriate screening 
 * for colorectal cancer
 */

// Value Sets
define "Colonoscopy Codes":
  { '45378', '45379', '45380', '45381', '45382', '45384', '45385', 
    '45386', '45388', '45389', '45390', '45391', '45392', '45393', '45398' }

define "FIT DNA Test Codes":
  { '81528' }

define "Fecal Occult Blood Test Codes":
  { '82270', '82274' }

// Measurement Period
define "Measurement Period End": Today()

define "Colonoscopy Lookback Start": 
  "Measurement Period End" - 10 years

define "FIT Lookback Start":
  "Measurement Period End" - 1 year

// Initial Population
define "In Initial Population":
  AgeInYearsAt("Measurement Period End") >= 45
    and AgeInYearsAt("Measurement Period End") <= 75

// Denominator
define "In Denominator":
  "In Initial Population"

// Numerator
define "Had Colonoscopy":
  exists (
    [Claim] C
      where exists (
        C.item I
          where exists (
            I.productOrService.coding CO
              where CO.code in "Colonoscopy Codes"
          )
      )
      and C.created during Interval["Colonoscopy Lookback Start", "Measurement Period End"]
  )

define "Had FIT or FIT DNA":
  exists (
    [Claim] C
      where exists (
        C.item I
          where exists (
            I.productOrService.coding CO
              where CO.code in ("FIT DNA Test Codes" union "Fecal Occult Blood Test Codes")
          )
      )
      and C.created during Interval["FIT Lookback Start", "Measurement Period End"]
  )

define "In Numerator":
  "Had Colonoscopy" or "Had FIT or FIT DNA"

// Denominator Exclusions
define "Had Total Colectomy":
  exists (
    [Condition] C
      where exists (
        C.code.coding CO
          where CO.code in { 'Z90.49' }  // Acquired absence of colon
      )
  )

define "In Denominator Exclusions":
  "Had Total Colectomy"

// Gap in Care
define "Gap in Care":
  "In Denominator" 
    and not "In Denominator Exclusions"
    and not "In Numerator"
