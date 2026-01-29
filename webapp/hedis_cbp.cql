library HEDISControllingBloodPressure version '1.0.0'

using FHIR version '4.0.1'

include FHIRHelpers version '4.0.1' called FHIRHelpers

context Patient

/*
 * HEDIS Controlling High Blood Pressure (CBP)
 * 
 * Description:
 * Percentage of patients 18-85 years of age who had a diagnosis of hypertension
 * and whose most recent blood pressure was adequately controlled (< 140/90 mmHg)
 * during the measurement period
 */

// Value Sets
define "Office Visit Codes":
  { '99201', '99202', '99203', '99204', '99205',
    '99211', '99212', '99213', '99214', '99215' }

define "Hypertension Diagnosis Codes":
  { 'I10', 'I11', 'I12', 'I13', 'I15' }  // Essential and secondary hypertension

// Measurement Period
define "Measurement Period End": Today()

define "Measurement Period Start":
  "Measurement Period End" - 1 year

// Initial Population
define "Has Hypertension":
  exists (
    [Condition] C
      where exists (
        C.code.coding CO
          where CO.code starts with 'I10'
            or CO.code starts with 'I11'
            or CO.code starts with 'I12'
            or CO.code starts with 'I13'
            or CO.code starts with 'I15'
      )
      and C.clinicalStatus ~ "active"
  )

define "In Initial Population":
  AgeInYearsAt("Measurement Period End") >= 18
    and AgeInYearsAt("Measurement Period End") <= 85
    and "Has Hypertension"

// Denominator
define "In Denominator":
  "In Initial Population"

// Numerator
// Note: This simplified implementation checks for office visits
// In a complete implementation, this would check actual BP readings from Observations
define "Had Office Visit with BP Check":
  exists (
    [Claim] C
      where exists (
        C.item I
          where exists (
            I.productOrService.coding CO
              where CO.code in "Office Visit Codes"
          )
      )
      and C.created during Interval["Measurement Period Start", "Measurement Period End"]
  )

define "In Numerator":
  "Had Office Visit with BP Check"
  // In complete implementation: and "Most Recent BP Controlled"

// Denominator Exclusions
define "Has End Stage Renal Disease":
  exists (
    [Condition] C
      where exists (
        C.code.coding CO
          where CO.code in { 'N18.6' }  // ESRD
      )
  )

define "In Denominator Exclusions":
  "Has End Stage Renal Disease"

// Gap in Care
define "Gap in Care":
  "In Denominator" 
    and not "In Denominator Exclusions"
    and not "In Numerator"
