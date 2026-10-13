# City data source probe

## MY state GDP real (API)

https://api.data.gov.my/data-catalogue?id=gdp_state_real_supply&limit=3

- HTTP 200
- content-type: `application/json` · 283 bytes · final URL: https://api.data.gov.my/data-catalogue/?id=gdp_state_real_supply&limit=3
- JSON (first 1500 chars):

```
[{"date": "2015-01-01", "state": "Johor", "value": 110002.221, "sector": "p0", "series": "abs"}, {"date": "2015-01-01", "state": "Johor", "value": 15610.314, "sector": "p1", "series": "abs"}, {"date": "2015-01-01", "state": "Johor", "value": 475.64, "sector": "p2", "series": "abs"}]
```

## MY catalogue page

https://open.dosm.gov.my/data-catalogue

- HTTP 200
- content-type: `text/html; charset=utf-8` · 487,369 bytes · final URL: https://open.dosm.gov.my/data-catalogue
- HTML title: Data Catalogue | OpenDOSM
- data-like links (0):
- body text (first 800 chars): Data Catalogue | OpenDOSM OpenDOSM Home Dashboards Data Catalogue Publications API Docs English English Home Dashboards Data Catalogue Publications API Docs Brought to you by the Visit our portal Department of Statistics Malaysia Brought to you by the Visit our portal Department of Statistics Malaysia DOSM's official open data portal Data Catalogue Your one-stop interface to browse our wealth of open data. This page will consistently grow in depth and breadth, providing richer and more varied data from the various divisions of DOSM. Select agency Category Demography Population Births Deaths Marriage Fertility Households Profile Income Poverty Inequality Expenditure Basic Amenities ICT Access National Accounts Gross Domestic Product Balance of Payments Education Education Infrastructure Edu

## MY archive per-capita by state

https://archive.data.gov.my/data/dataset/gross-domestic-product-gdp-per-capita-by-state-at-current-prices

- error: ConnectTimeout: HTTPSConnectionPool(host='archive.data.gov.my', port=443): Max retries exceeded with url: /data/dataset/gross-domestic-product-gdp-per-capita-by-state-at-current-prices (Caused by ConnectTimeoutError(<HTTPSConnection(host='archive.data.gov.my', port=443) at 0x7fca66d6d670>, 'Connection to archive.data.gov.my timed out. (connect timeout=60)'))

## PH per capita GDP prov/HUC (API meta)

https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2A/PPA/0092A5GPPA8.px

- HTTP 404

## PH API root

https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2A/PPA

- HTTP 200
- content-type: `application/json; charset=utf-8` · 1,220 bytes · final URL: https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2A/PPA
- JSON (first 1500 chars):

```
[{"id": "0012A5FPPA0.px", "type": "t", "text": "Gross Domestic Product by Province and HUC", "updated": "2026-08-28T09:25:02"}, {"id": "0022A5FPPA1.px", "type": "t", "text": "Gross Domestic Product by Industry, Province and HUC", "updated": "2026-08-28T09:25:45"}, {"id": "0032A5FPPA2.px", "type": "t", "text": "Gross Domestic Product by Province and HUC, Growth Rates", "updated": "2026-09-04T23:33:54"}, {"id": "0042A5FPPA3.px", "type": "t", "text": "Gross Domestic Product Growth Rates by Industry, Province and HUC", "updated": "2026-08-28T09:27:36"}, {"id": "0052A5FPPA4.px", "type": "t", "text": "Gross Domestic Product Percent Share by Province and HUC", "updated": "2026-08-28T09:28:09"}, {"id": "0062A5FPPA5.px", "type": "t", "text": "Gross Domestic Product Percent Share by Industry, Province and HUC", "updated": "2026-08-28T09:28:52"}, {"id": "0072A5FPPA6.px", "type": "t", "text": "Gross Domestic Product Implicit Price Index by Province and HUC", "updated": "2026-08-28T09:29:33"}, {"id": "0082A5FPPA7.px", "type": "t", "text": "Gross Domestic Product Implicit Price Index by Industry, Province and HUC", "updated": "2026-08-28T09:30:20"}, {"id": "0092A5FPPA8.px", "type": "t", "text": "Per Capita Gross Domestic Product by Province and HUC", "updated": "2026-08-28T09:30:50"}]
```

## TH NSO T10.1 2025

https://www.nso.go.th/public/e-book/Statistical-Yearbook/SYB-2025_webPage/File%20SYB/2025/10/T%2010.1%202025.pdf

- HTTP 200
- content-type: `application/pdf` · 69,038 bytes · final URL: https://www.nso.go.th/public/e-book/Statistical-Yearbook/SYB-2025_webPage/File%20SYB/2025/10/T%2010.1%202025.pdf
- PDF, 1 pages; page 1 text (first 1500 chars):

```
ตาราง 10.1 รายได้ประชาชาติสุทธิ ผลิตภัณฑ์มวลรวมประชาชาติ และรายจ่ายเพื�อการอุปโภคบริโภค 
พ.ศ. 2564 - 2566
Table 10.1 Net National Income, Gross National Product and Consumption Expenditure: 2021 - 2023
(จํานวนเป็นล้านบาท ต่อประชากรหนึ�งคนเป็นบาท  Million Baht, except per capita in Baht)
     2564r       2565        2566p
    (2021)       (2022)       (2023)
รายได้ประชาชาติสุทธิ Net National Income 
ราคาประจําปี......................................................... 12,583,740 13,694,707 14,336,930    Current market prices
180,573 196,056 204,693    Per capita
รายได้ประชาชาติ Gross National Income 
ราคาประจําปี......................................................... 15,624,338 16,824,279 17,505,174    Current market prices
224,204 240,860 249,928    Per capita
รายจ่ายเพื�อการอุปโภคบริโภคของครัวเรือน Consumption Expenditure of Households
ราคาประจําปี......................................................... 8,321,782 9,583,022 10,732,768    Current market prices
119,415 137,192 153,236    Per capita
   Chain volume measures
แบบปริมาณลูกโซ่ (ปีอ้างอิง พ.ศ. 2545)....... 5,619,082 6,120,103 6,704,765      (Reference year = 2002)
80,632 87,617 95,726    Per capita
General Government Consumption 
รายจ่ายเพื�อการอุปโภคของรัฐบาล   Expenditure
ราคาประจําปี......................................................... 2,951,660 3,079,209 2,983,435    Current market prices
42,355 44,083 42,596    Per capita
   Chain volume measures
แบบปริมาณลูกโซ่ (ปีอ้างอิง พ.ศ. 2545)....... 1,676,834 1,67
```

## TH NSO T10.14 2025

https://www.nso.go.th/public/e-book/Statistical-Yearbook/SYB-2025_webPage/File%20SYB/2025/10/T%2010.14%202025.pdf

- HTTP 200
- content-type: `application/pdf` · 109,409 bytes · final URL: https://www.nso.go.th/public/e-book/Statistical-Yearbook/SYB-2025_webPage/File%20SYB/2025/10/T%2010.14%202025.pdf
- PDF, 3 pages; page 1 text (first 1500 chars):

```
ตาราง  10.14 ผลิตภัณฑ์ภาค และจังหวัด จําแนกตามราคาประจําปี พ.ศ. 2564 - 2566
Table 10.14 Gross Regional and Provincial Product by Current Market Prices: 2021 - 2023
     2564r     2565      2566p     2564r     2565      2566p
    (2021)     (2022)     (2023)    (2021)     (2022)     (2023)
16,186,633 17,378,002 17,954,667 232,274 248,788 256,345
กรุงเทพมหานครและปริมณฑล 7,533,806 8,050,640 8,570,179 436,722 462,701 488,534 Bangkok and Vicinities
กรุงเทพมหานคร..……….……………… 5,319,930 5,689,128 6,142,910 588,899 627,732 675,979 Bangkok
สมุทรปราการ............………………… 653,913 727,452 757,502 285,730 312,660 320,294 Samut Prakan
นนทบุรี...............…………………………… 354,489 374,951 400,388 195,846 203,945 214,515 Nonthaburi
ปทุมธานี.............………………………… 419,916 449,256 460,312 231,471 243,998 246,463 Pathum Thani
นครปฐม............…………………………… 363,883 369,262 398,298 296,188 297,024 316,636 Nakhon Pathom
สมุทรสาคร.......…………………………. 421,675 440,591 410,768 391,955 405,453 374,056 Samut Sakhon
ภาคกลาง.………………….………… 884,340 900,039 881,689 278,706 283,891 278,250 Central Region
พระนครศรีอยุธยา..........…………… 426,035 413,406 393,943 465,830 451,158 428,870 Phra Nakhon Si Ayutthaya
อ่างทอง.........……………………………… 30,849 32,099 32,942 125,326 131,091 135,248 Ang Thong
ลพบุรี.............……………………………… 110,934 120,707 117,741 143,406 156,346 152,831 Lop Buri
สิงห์บุรี............……………………………… 26,432 27,938 27,785 142,226 151,471 151,750 Sing Buri
ชัยนาท............…………………………….. 39,632 43,027 45,036 13
```

## TH NESDC GRP page

https://www.nesdc.go.th/main.php?filename=gross_regional

- HTTP 200
- content-type: `text/html; charset=UTF-8` · 12,389,583 bytes · final URL: https://www.nesdc.go.th/info/economic-aspect/
- HTML title: ด้านเศรษฐกิจ - สำนักงานสภาพัฒนาการเศรษฐกิจและสังคมแห่งชาติ
- data-like links (6):
  - การบริหารงานด้าน ICT → /wp-content/uploads/2025/02/แผนปฏิบัติการดิจิทัล-สศช-2562-2564.pdf
  - การบริหารงานด้าน ICT → /wp-content/uploads/2025/02/แผนปฏิบัติการดิจิทัล-สศช-2562-2564.pdf
  - นโยบายเว็บไซต์ → https://www.nesdc.go.th/wordpress/wp-content/uploads/2025/09/NESDCWebsite_Policy.pdf
  - นโยบายการคุ้มครองข้อมูลส่วนบุคคล → https://www.nesdc.go.th/wordpress/wp-content/uploads/2025/09/NESDCPrivacy_Policy.pdf
  - นโยบายการรักษาความมั่นคงปลอดภัยของเว็บไซต์ → https://www.nesdc.go.th/wordpress/wp-content/uploads/2025/09/NESDCSecurity_Policy.pdf
  - นโยบายธรรมาภิบาลข้อมูล → https://www.nesdc.go.th/wordpress/wp-content/uploads/2026/06/นโยบายธรรมาภิบาลข้อมูล-ปรับหลังเวียน.pdf

## VN GSO EN home

https://www.gso.gov.vn/en/

- error: ConnectionError: HTTPSConnectionPool(host='www.gso.gov.vn', port=443): Max retries exceeded with url: /en/ (Caused by NameResolutionError("HTTPSConnection(host='www.gso.gov.vn', port=443): Failed to resolve 'www.gso.gov.vn' ([Errno -2] Name or service not known)"))

## VN NSO EN home

https://www.nso.gov.vn/en/

- HTTP 200
- content-type: `text/html; charset=UTF-8` · 107,925 bytes · final URL: https://www.nso.gov.vn/en/homepage/
- HTML title: National Statistics Office of Vietnam
- data-like links (0):
- body text (first 800 chars): National Statistics Office of Vietnam Skip to content About NSO NATIONAL STATISTICS OFFICE Search for: Population and employment Population Employment National accounts and Finance National Accounts Banking, insurance and State budget Economy Agriculture, Forestry and Fishery Investment and Construction Industry Enterprises Trade and Tourism Prices Society, Environment and Territory Science and technology, education Health, Culture, Sport, Living standards, Social order, Safety and Environment Administrative unit, Land and Climate Censuses Population and houses census Rural, agricultural and fishery census Economic census About NSO Address Development history Functions and duties Organizational structure Population and employment Population Employment National accounts and Finance National

## VN PX-Web

https://pxweb.gso.gov.vn/pxweb/en/

- error: ConnectionError: HTTPSConnectionPool(host='pxweb.gso.gov.vn', port=443): Max retries exceeded with url: /pxweb/en/ (Caused by NameResolutionError("HTTPSConnection(host='pxweb.gso.gov.vn', port=443): Failed to resolve 'pxweb.gso.gov.vn' ([Errno -2] Name or service not known)"))

## ID BPS PDRB per kapita table search

https://www.bps.go.id/en/statistics-table?subject=528

- HTTP 403

## UN WUP downloads (cities)

https://population.un.org/wup/downloads?tab=Cities

- HTTP 200
- content-type: `text/html` · 69,675 bytes · final URL: https://population.un.org/wup/downloads?tab=Cities
- HTML title: World Urbanization Prospects
- data-like links (6):
  - Download Center → /wup/downloads
  - Definition of Regions → /wup/downloads?tab=Sources%20and%20Documentation
  - WUP2025-F01-Degree-of-Urbanization_Pop_by_category → assets/Download/Countries and Aggregates/WUP2025-F01-Degree-of-Urbanization_Pop_by_category.xlsx
  - WUP2025-F02-Degree-of-Urbanization_percPop_by_category → assets/Download/Countries and Aggregates/WUP2025-F02-Degree-of-Urbanization_percPop_by_category.xlsx
  - WUP2025-F03-Degree-of-Urbanization_Pop_rate_by_category → assets/Download/Countries and Aggregates/WUP2025-F03-Degree-of-Urbanization_Pop_rate_by_category.xlsx
  - WUP2025-F04-Degree-of-Urbanization_percPop_rate_by_category → assets/Download/Countries and Aggregates/WUP2025-F04-Degree-of-Urbanization_percPop_rate_by_category.xlsx

## UN WUP home

https://population.un.org/wup/

- HTTP 200
- content-type: `text/html` · 66,742 bytes · final URL: https://population.un.org/wup/
- HTML title: World Urbanization Prospects
- data-like links (4):
  - Download Center → /wup/downloads
  - Definition of Regions → /wup/downloads?tab=Sources%20and%20Documentation
  - series of Excel files → /wup/downloads
  - CSV format → /wup/downloads
