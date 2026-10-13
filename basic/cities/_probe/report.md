# City data source probe

## PH per capita GDP prov/HUC (meta)

https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2A/PPA/0092A5FPPA8.px

- HTTP 200
- content-type: `application/json; charset=utf-8` · 3,667 bytes · final URL: https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2A/PPA/0092A5FPPA8.px
- JSON (first 1500 chars):

```
{"title": "Per Capita Gross Domestic Product by Province and HUC", "variables": [{"code": "Geolocation", "text": "Geolocation", "values": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73", "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85", "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97", "98", "99", "100", "101", "102", "103", "104", "105", "106", "107", "108", "109", "110", "111", "112", "113", "114", "115", "116", "117", "118", "119", "120", "121", "122", "123", "124", "125", "126", "127", "128", "129", "130", "131", "132", "133", "134"], "valueTexts": ["National Capital Region (NCR)", "..City of Caloocan", "..City of Las Piñas", "..City of Makati", "..City of Malabon", "..City of Mandaluyong", "..City of Manila", "..City of Marikina", "..City of Muntinlupa", "..City of Navotas", "..City of Parañaque", "..Pasay City", "..City of Pasig", "..Quezon City", "..City of San Juan", "..City of Taguig", "..City of Valenzuela", "..Pateros", "Cordillera Administrative Region (CAR)", "..Abra", "..Apayao", "..Benguet", "..Ifugao", "..Kalinga", "..Mountain Province", 
```

## MY state GDP nominal? (API)

https://api.data.gov.my/data-catalogue?id=gdp_state_nominal_supply&limit=2

- HTTP 404

## VN NSO search: yearbook

https://www.nso.gov.vn/en/?s=statistical+yearbook

- HTTP 200
- content-type: `text/html; charset=UTF-8` · 127,840 bytes · final URL: https://www.nso.gov.vn/en/?s=statistical+yearbook
- HTML title: Search Results for “statistical yearbook” – National Statistics Office of Vietnam
- data-like links (1):
  - Statistical Yearbook of Vietnam 2010 → https://www.nso.gov.vn/wp-content/uploads/2019/10/NGTK-2010-pdf.pdf

## VN NSO search: GRDP

https://www.nso.gov.vn/en/?s=GRDP+per+capita

- HTTP 200
- content-type: `text/html; charset=UTF-8` · 81,792 bytes · final URL: https://www.nso.gov.vn/en/?s=GRDP+per+capita
- HTML title: Search Results for “GRDP per capita” – National Statistics Office of Vietnam
- data-like links (0):
- body text (first 800 chars): Search Results for “GRDP per capita” – National Statistics Office of Vietnam Skip to content About NSO NATIONAL STATISTICS OFFICE Search for: Population and employment Population Employment National accounts and Finance National Accounts Banking, insurance and State budget Economy Agriculture, Forestry and Fishery Investment and Construction Industry Enterprises Trade and Tourism Prices Society, Environment and Territory Science and technology, education Health, Culture, Sport, Living standards, Social order, Safety and Environment Administrative unit, Land and Climate Censuses Population and houses census Rural, agricultural and fishery census Economic census About NSO Address Development history Functions and duties Organizational structure Population and employment Population Employment

## ID BPS EN home

https://www.bps.go.id/en

- HTTP 403

## ID BPS Jakarta

https://jakarta.bps.go.id/en

- HTTP 403

## MY catalogue ids containing gdp

https://open.dosm.gov.my/data-catalogue

- HTTP 200; 35 matches:
  - `gdp_annual_nominal_demand`
  - `gdp_annual_nominal_demand_granular`
  - `gdp_annual_nominal_demand_sub`
  - `gdp_annual_nominal_income`
  - `gdp_annual_nominal_supply`
  - `gdp_annual_nominal_supply_granular`
  - `gdp_annual_nominal_supply_sub`
  - `gdp_annual_real_demand`
  - `gdp_annual_real_demand_granular`
  - `gdp_annual_real_demand_sub`
  - `gdp_annual_real_supply`
  - `gdp_annual_real_supply_granular`
  - `gdp_annual_real_supply_sub`
  - `gdp_district_real_supply`
  - `gdp_gni_annual_nominal`
  - `gdp_gni_annual_real`
  - `gdp_lookup`
  - `gdp_qtr_nominal`
  - `gdp_qtr_nominal_demand`
  - `gdp_qtr_nominal_demand_granular`
  - `gdp_qtr_nominal_demand_sub`
  - `gdp_qtr_nominal_supply`
  - `gdp_qtr_nominal_supply_granular`
  - `gdp_qtr_nominal_supply_sub`
  - `gdp_qtr_real`
  - `gdp_qtr_real_demand`
  - `gdp_qtr_real_demand_granular`
  - `gdp_qtr_real_demand_sub`
  - `gdp_qtr_real_sa`
  - `gdp_qtr_real_sa_demand`
  - `gdp_qtr_real_sa_supply`
  - `gdp_qtr_real_supply`
  - `gdp_qtr_real_supply_granular`
  - `gdp_qtr_real_supply_sub`
  - `gdp_state_real_supply`

## UN WUP file names

https://population.un.org/wup/downloads?tab=Cities

- HTTP 200; 75 matches:
  - `WUP2025-DB-DEGURBA-Cities-Population-Surface-Data.csv`
  - `WUP2025-DB-DEGURBA-Level1-Population-Surface-Data.csv`
  - `WUP2025-DB-DEGURBA-Level2-Population-Surface-Data.csv`
  - `WUP2025-DB-DEGURBA-Population-by-size-class-of-cities.csv`
  - `WUP2025-DB-National-Definitions-Population-Data.csv`
  - `WUP2025-DB-SA-DEGURBA-Level1-Population-Surface-Data.csv`
  - `WUP2025-DB-SA-DEGURBA-Level2-Population-Surface-Data.csv`
  - `WUP2025-F00-LOCATIONS.xlsx`
  - `WUP2025-F01-Degree-of-Urbanization_Pop_by_category.xlsx`
  - `WUP2025-F02-Degree-of-Urbanization_percPop_by_category.xlsx`
  - `WUP2025-F03-Degree-of-Urbanization_Pop_rate_by_category.xlsx`
  - `WUP2025-F04-Degree-of-Urbanization_percPop_rate_by_category.xlsx`
  - `WUP2025-F05-Degree-of-Urbanization_AREA_km2_by_category.xlsx`
  - `WUP2025-F06-Degree-of-Urbanization_percAREA_km2_by_category.xlsx`
  - `WUP2025-F07-Degree-of-Urbanization_AREA_km2_rate_by_category.xlsx`
  - `WUP2025-F08-Degree-of-Urbanization_percAREA_km2_rate_by_category.xlsx`
  - `WUP2025-F09-Degree-of-Urbanization_BU_km2_by_category.xlsx`
  - `WUP2025-F10-Degree-of-Urbanization_BU_m2_per_capita_by_category.xlsx`
  - `WUP2025-F11-Degree-of-Urbanization_percBU_km2_by_category.xlsx`
  - `WUP2025-F12-Degree-of-Urbanization_BU_km2_rate_by_category.xlsx`
  - `WUP2025-F13-Degree-of-Urbanization_percBU_km2_rate_by_category.xlsx`
  - `WUP2025-F14-National-Definitions_Pop_by_category.xlsx`
  - `WUP2025-F15-National-Definitions_percPop_by_category.xlsx`
  - `WUP2025-F16-National-Definitions_Pop_rate_by_category.xlsx`
  - `WUP2025-F17-National-Definitions_percPop_rate_by_category.xlsx`
  - `WUP2025-M01-DataSources-Degree-of-Urbanization.xlsx`
  - `WUP2025-M02-DataSources-National-Definitions-UrbanPercentage.xlsx`
  - `assets/Download/Archive/WUP1992-Excel-Files.zip`
  - `assets/Download/Archive/WUP1994-Excel-Files.zip`
  - `assets/Download/Archive/WUP1999-Excel-Files.zip`
  - `assets/Download/Archive/WUP2003-Excel-files.zip`
  - `assets/Download/Archive/WUP2005-Excel-files.zip`
  - `assets/Download/Archive/WUP2007-Excel-files.zip`
  - `assets/Download/Archive/WUP2009-Excel-files.zip`
  - `assets/Download/Archive/WUP2011-Excel-files.zip`
  - `assets/Download/Archive/WUP2014-Excel-files.zip`
  - `assets/Download/Archive/WUP2018-Excel-files.zip`
  - `assets/Download/Cities/WUP2025-DB-DEGURBA-Cities-Population-Surface-Data.csv.gz`
  - `assets/Download/Cities/WUP2025-DB-DEGURBA-Population-by-size-class-of-cities.csv.gz`
  - `assets/Download/Cities/WUP2025-F18-DEGURBA-100_Largest_Cities.xlsx`
  - `assets/Download/Cities/WUP2025-F19-DEGURBA-100_Largest_Cities_in_2025_by_time.xlsx`
  - `assets/Download/Cities/WUP2025-F20-DEGURBA-Capital_Cities.xlsx`
  - `assets/Download/Cities/WUP2025-F21-DEGURBA-Cities_Pop.xlsx`
  - `assets/Download/Cities/WUP2025-F22-DEGURBA-Cities_percPop.xlsx`
  - `assets/Download/Cities/WUP2025-F23-DEGURBA-Cities_Pop_rate.xlsx`
  - `assets/Download/Cities/WUP2025-F24-DEGURBA-Cities_percPop_rate.xlsx`
  - `assets/Download/Cities/WUP2025-F25-DEGURBA-Cities_AREA_km2.xlsx`
  - `assets/Download/Cities/WUP2025-F26-DEGURBA-Cities_percAREA_km2.xlsx`
  - `assets/Download/Cities/WUP2025-F27-DEGURBA-Cities_AREA_km2_rate.xlsx`
  - `assets/Download/Cities/WUP2025-F28-DEGURBA-Cities_percAREA_km2_rate.xlsx`
  - `assets/Download/Cities/WUP2025-F29-DEGURBA-Cities_BU_AREA_km2.xlsx`
  - `assets/Download/Cities/WUP2025-F30-DEGURBA-Cities_BU_m2_per_capita.xlsx`
  - `assets/Download/Cities/WUP2025-F31-DEGURBA-Cities_percBU_km2.xlsx`
  - `assets/Download/Cities/WUP2025-F32-DEGURBA-Cities_BU_km2_rate.xlsx`
  - `assets/Download/Cities/WUP2025-F33-DEGURBA-Cities_percBU_km2_rate.xlsx`
  - `assets/Download/Cities/WUP2025-F34-DEGURBA-Cities_Pop_density.xlsx`
  - `assets/Download/Cities/WUP2025-F34-DEGURBA_Cities_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F35-DEGURBA_Pop_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F36-DEGURBA_percPop_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F37-DEGURBA_Pop_rate_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F38-DEGURBA_percPop_rate_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F39-DEGURBA_AREA_km2_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F40-DEGURBA_percAREA_km2_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F41-DEGURBA_AREA_km2_rate_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F42-DEGURBA_percAREA_km2_rate_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F43-DEGURBA_BU_km2_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F44-DEGURBA_BU_m2_per_capita_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F45-DEGURBA_percBU_km2_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F46-DEGURBA_BU_km2_rate_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025-F47-DEGURBA_percBU_km2_rate_by_City_Size_Class.xlsx`
  - `assets/Download/Cities/WUP2025_Cities_Indicators.csv`
  - `assets/Download/Countries`
  - `assets/Download/WUP2025-F00-LOCATIONS.xlsx`
  - `assets/Download/WUP2025-M01-DataSources-Degree-of-Urbanization.xlsx`
  - `assets/Download/WUP2025-M02-DataSources-National-Definitions-UrbanPercentage.xlsx`
