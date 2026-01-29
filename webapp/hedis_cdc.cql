library HEDISComprehensiveDiabetesCare version '1.0.0'

using FHIR version '4.0.1'

include FHIRHelpers version '4.0.1' called FHIRHelpers

context Patient

/*
 * HEDIS Comprehensive Diabetes Care - HbA1c Testing (CDC)
 * 
 * Description:
 * Percentage of patients 18-75 years of age with diabetes (type 1 and type 2)
 * who had HbA1c testing performed during the measurement year
 */

// Value Sets
define "HbA1c Test Codes":
  { '83036', '83037' }

define "Diabetes Diagnosis Codes":
  { 'E10', 'E11', 'E13' }  // Type 1, Type 2, Other specified diabetes

// Measurement Period
define "Measurement Period End": Today()

define "Measurement Period Start":
  "Measurement Period End" - 1 year

// Initial Population
define "Has Diabetes":
  exists (
    [Condition] C
      where exists (
        C.code.coding CO
          where CO.code starts with 'E10'
            or CO.code starts with 'E11'
            or CO.code starts with 'E13'
      )
      and C.clinicalStatus ~ "active"
  )

define "In Initial Population":
  AgeInYearsAt("Measurement Period End") >= 18
    and AgeInYearsAt("Measurement Period End") <= 75
    and "Has Diabetes"

// Denominator
define "In Denominator":
  "In Initial Population"

// Numerator
define "Had HbA1c Test":
  exists (
    [Claim] C
      where exists (
        C.item I
          where exists (
            I.productOrService.coding CO
              where CO.code in "HbA1c Test Codes"
          )
      )
      and C.created during Interval["Measurement Period Start", "Measurement Period End"]
  )

define "In Numerator":
  "Had HbA1c Test"

// Denominator Exclusions
define "In Denominator Exclusions":
  false  // No exclusions for this measure

// Gap in Care
define "Gap in Care":
  "In Denominator" and not "In Numerator"
