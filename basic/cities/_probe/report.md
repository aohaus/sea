# City data source probe

## PH per capita GDP prov/HUC (meta, full)

https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2A/PPA/0092A5FPPA8.px

- HTTP 200
- content-type: `application/json; charset=utf-8` · 3,667 bytes · final URL: https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2A/PPA/0092A5FPPA8.px
- JSON (first 1500 chars):

```
{"title": "Per Capita Gross Domestic Product by Province and HUC", "variables": [{"code": "Geolocation", "text": "Geolocation", "values": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73", "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85", "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97", "98", "99", "100", "101", "102", "103", "104", "105", "106", "107", "108", "109", "110", "111", "112", "113", "114", "115", "116", "117", "118", "119", "120", "121", "122", "123", "124", "125", "126", "127", "128", "129", "130", "131", "132", "133", "134"], "valueTexts": ["National Capital Region (NCR)", "..City of Caloocan", "..City of Las Piñas", "..City of Makati", "..City of Malabon", "..City of Mandaluyong", "..City of Manila", "..City of Marikina", "..City of Muntinlupa", "..City of Navotas", "..City of Parañaque", "..Pasay City", "..City of Pasig", "..Quezon City", "..City of San Juan", "..City of Taguig", "..City of Valenzuela", "..Pateros", "Cordillera Administrative Region (CAR)", "..Abra", "..Apayao", "..Benguet", "..Ifugao", "..Kalinga", "..Mountain Province", "..City of Baguio", "Region I (Ilocos Region)", "..Ilocos Norte", "..Ilocos Sur", "..La Union", "..Pangasinan", "Region II (Cagayan Valley)", "..Batanes", "..Cagayan", "..Isabela", "..Nueva Vizcaya", "..Quirino", "Region III (Central Luzon)", "..Aurora", "..Bataan", "..Bulacan", "..Nueva Ecija", "..Pampanga", "..Tarlac", "..Zambales", "..City of Angeles", "..City of Olongapo", "Region IV-A (CALABARZON)", "..Batangas", "..Cavite", "..Laguna", "..Quezon", "..Rizal", "..City of Lucena", "MIMAROPA Region", "..Marinduque", "..Occidental Mindoro", "..Oriental Mindoro", "..Palawan", "..Romblon", "..City of Puerto Princesa", "Region V (Bicol Region)", "..Albay", "..Camarines Norte", "..Camarines Sur", "..Catanduanes", "..Masbate", "..Sorsogon", "Region VI (Western Visayas)", "..Aklan", "..Antique", "..Capiz", "..Guimaras", "..Iloilo", "..City of Iloilo", "Negros Island Region (NIR)", "..Negros Occidental", "..Negros Oriental", "..Siquijor", "..City of Bacolod", "Region VII (Central Visayas)", "..Bohol", "..Cebu", "..City of Cebu", "..City of Lapu-Lapu", "..City of Mandaue", "Region VIII (Eastern Visayas)", "..Biliran", "..Eastern Samar", "..Leyte", "..Northern Samar", "..Samar", "..Southern Leyte", "..City of Tacloban", "Region IX (Zamboanga Peninsula)", "..Sulu", "..Zamboanga del Norte", "..Zamboanga del Sur", "..Zamboanga Sibugay", "..City of Isabela", "..City of Zamboanga", "Region X (Northern Mindanao)", "..Bukidnon", "..Camiguin", "..Lanao del Norte", "..Misamis Occidental", "..Misamis Oriental", "..City of Cagayan de Oro", "..City of Iligan", "Region XI (Davao Region)", "..Davao de Oro", "..Davao del Norte", "..Davao del Sur", "..Davao Occidental", "..Davao Oriental", "..City of Davao", "Region XII (SOCCSKSARGEN)", "..Cotabato", "..Sarangani", "..South Cotabato", "..Sultan Kudarat", "..City of General Santos", "Region XIII (Caraga)", "..Agusan del Norte", "..Agusan del Sur", "..Dinagat Islands", "..Surigao del Norte", "..Surigao del Sur", "..City of Butuan", "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)", "..Basilan", "..Lanao del Sur", "..Maguindanao del Norte", "..Maguindanao del Sur", "..Tawi-Tawi"]}, {"code": "Type of Valuation", "text": "Type of Valuation", "values": ["0", "1"], "valueTexts": ["At Current Prices", "At Constant 2018 Prices"]}, {"code": "Year", "text": "Year", "values": ["0", "1", "2", "3", "4", "5", "6", "7"], "valueTexts": ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"], "time": true}]}
```

## MY archive CKAN package (per capita by state, current)

https://archive.data.gov.my/data/api/3/action/package_show?id=gross-domestic-product-gdp-per-capita-by-state-at-current-prices

- error: ConnectTimeout: HTTPSConnectionPool(host='archive.data.gov.my', port=443): Max retries exceeded with url: /data/api/3/action/package_show?id=gross-domestic-product-gdp-per-capita-by-state-at-current-prices (Caused by ConnectTimeoutError(<HTTPSConnection(host='archive.data.gov.my', port=443) at 0x7f006be1eea0>, 'Connection to archive.data.gov.my timed out. (connect timeout=60)'))

## MY population by state (API)

https://api.data.gov.my/data-catalogue?id=population_state&limit=3

- HTTP 200
- content-type: `application/json` · 408 bytes · final URL: https://api.data.gov.my/data-catalogue/?id=population_state&limit=3
- JSON (first 1500 chars):

```
[{"age": "overall_age", "sex": "overall_sex", "date": "2020-01-01", "state": "Johor", "ethnicity": "overall_ethnicity", "population": 4009.7}, {"age": "0-4", "sex": "overall_sex", "date": "2020-01-01", "state": "Johor", "ethnicity": "overall_ethnicity", "population": 306.3}, {"age": "5-9", "sex": "overall_sex", "date": "2020-01-01", "state": "Johor", "ethnicity": "overall_ethnicity", "population": 322.3}]
```

## MY state GDP real (API, KL rows)

https://api.data.gov.my/data-catalogue?id=gdp_state_real_supply&filter=W.P.%20Kuala%20Lumpur@state&limit=12

- HTTP 200
- content-type: `application/json` · 2 bytes · final URL: https://api.data.gov.my/data-catalogue/?id=gdp_state_real_supply&filter=W.P.%20Kuala%20Lumpur@state&limit=12
- JSON (first 1500 chars):

```
[]
```

## VN NSO search: Statistical Yearbook 2024

https://www.nso.gov.vn/en/?s=Statistical+Yearbook+of+Vietnam+2024

- HTTP 200
- content-type: `text/html; charset=UTF-8` · 66,163 bytes · final URL: https://www.nso.gov.vn/en/?s=Statistical+Yearbook+of+Vietnam+2024
- HTML title: Search Results for “Statistical Yearbook of Vietnam 2024” – National Statistics Office of Vietnam
- data-like links (0):
- body text (first 800 chars): Search Results for “Statistical Yearbook of Vietnam 2024” – National Statistics Office of Vietnam Skip to content About NSO NATIONAL STATISTICS OFFICE Search for: Population and employment Population Employment National accounts and Finance National Accounts Banking, insurance and State budget Economy Agriculture, Forestry and Fishery Investment and Construction Industry Enterprises Trade and Tourism Prices Society, Environment and Territory Science and technology, education Health, Culture, Sport, Living standards, Social order, Safety and Environment Administrative unit, Land and Climate Censuses Population and houses census Rural, agricultural and fishery census Economic census About NSO Address Development history Functions and duties Organizational structure Population and employment 

## VN NSO data-and-statistics

https://www.nso.gov.vn/en/data-and-statistics/

- HTTP 200
- content-type: `text/html; charset=UTF-8` · 83,340 bytes · final URL: https://www.nso.gov.vn/en/data-and-statistics/
- HTML title: Data and statistics – National Statistics Office of Vietnam
- data-like links (0):
- body text (first 800 chars): Data and statistics – National Statistics Office of Vietnam Skip to content About NSO NATIONAL STATISTICS OFFICE Search for: Population and employment Population Employment National accounts and Finance National Accounts Banking, insurance and State budget Economy Agriculture, Forestry and Fishery Investment and Construction Industry Enterprises Trade and Tourism Prices Society, Environment and Territory Science and technology, education Health, Culture, Sport, Living standards, Social order, Safety and Environment Administrative unit, Land and Climate Censuses Population and houses census Rural, agricultural and fishery census Economic census About NSO Address Development history Functions and duties Organizational structure Population and employment Population Employment National account

## UN WUP F21 cities pop (HEAD)

https://population.un.org/wup/assets/Download/Cities/WUP2025-F21-DEGURBA-Cities_Pop.xlsx

- HTTP 200
- content-type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` · 10,671,837 bytes · final URL: https://population.un.org/wup/assets/Download/Cities/WUP2025-F21-DEGURBA-Cities_Pop.xlsx
- sheet `info`
  -  |  |  |  |  |  |  | 
  -  |  |  |  |  |  |  | 
  -  |  |  |  |  |  |  | 
  -  |  |  |  |  |  |  | 
  -  |  |  | United Nations |  |  |  | 
  -  |  |  | Population Division |  |  |  | 
  -  |  |  | Department of Economic and Soc |  |  |  | 
  -  |  |  |  |  |  |  | 
  -  |  |  | World Urbanization Prospects:  |  |  |  | 
  -  |  |  | File 21: Population Residing i |  |  |  | 
  -  |  |  |  |  |  |  | 
  -  |  |  | POP/DB/WUP/Rev.2025/F21 |  |  |  | 
  -  |  |  | Copyright © 2025 by United Nat |  |  |  | 
  -  |  |  | Suggested citation: United Nat |  |  |  | 
  -  |  |  |  |  |  |  | 
  -  |  |  |  |  |  |  | 
  - Data are presented  in the fol |  |  |  |  |  |  | 
  -  |  |  |  |  |  |  | 
  - The following set of criteria  |  |  |  |  |  |  | 
  - Cities (densely populated area |  |  |  |  |  |  | 
  -  |  |  |  |  |  |  | 
  - The following column names des |  |  |  |  |  |  | 
  - Field | Description |  |  |  |  |  | 
  - Index | Row number (used for sorting d |  |  |  |  |  | 
  - Location | Name of region, subregion, cou |  |  |  |  |  | 
- sheet `Data`
  - Index | Location | Notes | LocID | ISO3_Code | ISO2_Code | City_Code | City_Name | Capital | PWCent_Longitude | PWCent_Latitude | 1975 | 1976 | 1977
  - 1 | Afghanistan |  | 4 | AFG | AF | 13322 | Achin | 0 | 70.7024930218106 | 34.0984706711626 |  |  | 
  - 2 | Afghanistan |  | 4 | AFG | AF | 12267 | Almar | 0 | 64.5224568785344 | 35.8511516133353 |  |  | 
  - 3 | Afghanistan |  | 4 | AFG | AF | 1881 | Andkhoy | 0 | 65.1003874569346 | 36.9340682077702 |  |  | 
  - 4 | Afghanistan |  | 4 | AFG | AF | 12335 | Aqcha | 0 | 66.1859806567253 | 36.8994798730738 |  |  | 
  - 5 | Afghanistan |  | 4 | AFG | AF | 12546 | Asadabad | 0 | 71.1559145088556 | 34.8742235217772 |  |  | 
  - 6 | Afghanistan |  | 4 | AFG | AF | 4087 | Baghlan | 0 | 68.7520961315393 | 36.1792150061817 |  |  | 
  - 7 | Afghanistan |  | 4 | AFG | AF | 4847 | Bagram | 0 | 69.2633328062887 | 34.9411588985322 |  |  | 
  - 8 | Afghanistan |  | 4 | AFG | AF | 13295 | Baharak | 0 | 70.8911668066793 | 36.9967136557767 |  |  | 
  - 9 | Afghanistan |  | 4 | AFG | AF | 1964 | Bai Ghesi | 0 | 64.6622531792966 | 36.0475237064719 |  |  | 
  - 10 | Afghanistan |  | 4 | AFG | AF | 1211 | Bala Murghab | 0 | 63.3313201394643 | 35.5797601891393 |  |  | 
  - 11 | Afghanistan |  | 4 | AFG | AF | 13149 | Balkh | 0 | 66.8949133014981 | 36.755559410662 |  |  | 
  - 12 | Afghanistan |  | 4 | AFG | AF | 4001 | Bamian | 0 | 67.8261187801473 | 34.8151166915502 |  |  | 
  - 13 | Afghanistan |  | 4 | AFG | AF | 1099 | Bandabad | 0 | 62.6950114035859 | 34.2335642065164 |  |  | 
  - 14 | Afghanistan |  | 4 | AFG | AF | 4952 | Baraki Rijan | 0 | 68.9529301151118 | 33.9478564732283 |  |  | 
  - 15 | Afghanistan |  | 4 | AFG | AF | 13216 | Bazar-e Panjva'i | 0 | 65.4637389208366 | 31.5409606189046 |  |  | 
  - 16 | Afghanistan |  | 4 | AFG | AF | 4481 | Bed-i-Kalan | 0 | 70.3100155507096 | 37.3453686362921 |  |  | 
  - 17 | Afghanistan |  | 4 | AFG | AF | 3628 | Bomay | 0 | 66.2505577557935 | 33.3802190180606 |  |  | 
  - 18 | Afghanistan |  | 4 | AFG | AF | 15457 | Bursanak | 0 | 68.0385731273608 | 34.6555968076023 |  |  | 
  - 19 | Afghanistan |  | 4 | AFG | AF | 4555 | Charikar | 0 | 69.1695330444007 | 35.0162128356321 | 82.727 | 82.537 | 82.347
  - 20 | Afghanistan |  | 4 | AFG | AF | 4254 | Chayab | 0 | 69.8100992684208 | 37.396446911667 |  |  | 
  - 21 | Afghanistan |  | 4 | AFG | AF | 15352 | Chemtal | 0 | 66.8281837537792 | 36.6899615671489 |  |  | 
  - 22 | Afghanistan |  | 4 | AFG | AF | 14110 | Chowkey | 0 | 70.908632316728 | 34.67169803573 |  |  | 
  - 23 | Afghanistan |  | 4 | AFG | AF | 14753 | Dahan-e Bāy | 0 | 67.7619158822166 | 34.4029742943458 |  |  | 
  - 24 | Afghanistan |  | 4 | AFG | AF | 15323 | Darah | 0 | 65.2510610500605 | 35.1112738011163 |  |  | 
- sheet `NOTES`
  - Notes |  |  | 
  - * | The designations employed and  |  | 
  - ** | SDMX Global Registry: Cross Do |  | 
  - a | Countries and areas are groupe |  | 
  - b | Sub-Saharan Africa refers to a |  | 
  - c | The designation “more develope |  | 
  - d | More developed regions compris |  | 
  - e | Less developed regions compris |  | 
  - f | The group of least developed c |  | 
  - g | Other less developed countries |  | File 22: Percentage of the Cit
  - h | The group of Landlocked Develo |  | 
  - i | The group of Small Island Deve |  | 
  - j | The country classification by  |  | 
  - k | Countries and areas are groupe |  | 
  - 1 | Including Agalega, Rodrigues a |  | 
  - 2 | For statistical purposes, the  |  | 
  - 3 | Including Zanzibar. |  | 
  - 4 | Including Ascension and Trista |  | 
  - 5 | For statistical purposes, the  |  | 
  - 6 | As of 1 July 1997, Hong Kong b |  | 
  - 7 | As of 20 December 1999, Macao  |  | 
  - 8 | For statistical purposes, the  |  | 
  - 9 | Including Sabah and Sarawak. |  | 
  - 10 | Including Nagorno-Karabakh. |  | 
  - 11 | Refers to the whole country. |  | 
