# housing-api

## 1. Overview
This project implements a RESTful Web API that provides analytical insights
into the UK housing market by integrating HM Land Registry(England and Wales) and ONS(UK) datasets.

The API supports full CRUD operations on housing transactions and locations,
and exposes additional analytical endpoints for regional price trends,
median prices, and affordability indicators.
## 2. Features
## 3. Tech Stack
- Language: Python 3.13
- Framework: FastAPI
- Database: Sqlite
- ORM SQLALchemy
- API Documentation: Swagger / OpenAPI
## 4. Project Structure
## 5. Setup & Installation
## 6. Running the Project
## 7. API Documentation
### 7.1 Areas
- GET /areas
  - Purpose: List all areas (Supports ?q= fuzzy search)
  - Responses
    - 200 OK – returns list
    - 400 Bad Request – invalid query param
- GET /areas/{area_code}
  - Purpose: Search a single area by area code
  - Responses
    - 200 OK – returns single area object
    - 400 Bad Request – invalid query param
<!--- POST /areas
  - Purpose: Create an area
  - Responses
    - 201 Created – successfully created 
    - 400 Bad Request – invalid input 
    - 409 Conflict – area_code already exists
- PUT /areas/{area_code}
  - Purpose: Update area name
  - Responses
    - 200 OK – successfully updated 
    - 400 Bad Request – invalid data 
    - 404 Not Found – area not found
- DELETE /areas/{area_code}
  - Purpose: Delete area (If postcode_map/rent_stats is a dependency, a 409 error may occur).
  - Responses
    - 204 No Content – successfully deleted 
    - 404 Not Found – area not found 
    - 409 Conflict – area has dependent records-->
### 7.2 Postcode
- GET /postcodes/{postcode}
  - Purpose: Find which area an individual postcode belongs to.
  - Responses 
    - 200 OK – returns mapping 
    - 404 Not Found – postcode not found 
    - 400 Bad Request – invalid postcode format
- GET /areas/{area_code}/postcodes 
  - Purpose: List all postcodes within a specific area.
  - Responses 
    - 200 OK – returns list (possibly empty)
    - 404 Not Found – area not found
- GET /postcodes 
  - Purpose: Search postcodes (useful for fuzzy search / prefix search)
  - Responses 
    - 200 OK – returns list
### 7.3 Rent Stats
  - GET /rent-stats
    - Purpose: Retrieve rent statistics for a given area and time period.
    - Query params (required):
      - area_code (string)
      - time_period (string, YYYY-MM)
    - Responses:
      - 200 OK – returns stats object 
      - 404 Not Found – no data available for the given inputs 
      - 400 Bad Request – missing/invalid parameters 
  - GET /areas/{area_code}/rent-stats 
    - Purpose: Retrieve rent statistics time-series for an area.
    - Query params (optional):
      - from (string, YYYY-MM)
      - to (string, YYYY-MM)
    - Responses:
      - 200 OK – returns list (possibly empty)
      - 404 Not Found – area not found 
  - GET /areas/{area_code}/rent-stats/latest 
    - Purpose: Retrieve the latest available rent statistics for an area. 
    - Responses:
      - 200 OK – returns latest stats 
      - 404 Not Found – no data available for this area
### 7.4 Official Sales Transactions
- GET /official/sales-transactions 
  - Purpose: List official property sale transactions imported from HM Land Registry (supports search/filtering). 
  - Responses:
    - 200 OK – returns list (possibly empty)
- GET /official/sales-transactions/{transaction_uuid} 
  - Purpose: Retrieve a single official sale transaction by UUID. 
  - Responses:
    - 200 OK – returns single transaction object 
    - 404 Not Found – transaction not found

- GET /official/areas/{area_code}/sales-transactions 
  - Purpose: List official sale transactions within a specific area (derived via postcode → area mapping). 
  - Responses:
    - 200 OK – returns list (possibly empty)
    - 404 Not Found – area not found 

- GET /official/postcodes/{postcode}/sales-transactions 
  - Purpose: List official sale transactions for a given postcode. 
  - Responses:
    - 200 OK – returns list (possibly empty)
    - 404 Not Found – postcode not found
## 8. Example Usage
## 9. Data Sources
- Housing Price: Statistical data set Price Paid Data
  - URL: https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads
- Renting Price: Price Index of Private Rents, UK: monthly price statistics
  - URL: https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/priceindexofprivaterentsukmonthlypricestatistics
- National Statistics Postcode Lookup
  - URL: https://geoportal.statistics.gov.uk/datasets/8a1d5b58df824b2e86fe07ddfdd87165/about 
## 10. Testing
## 11. Limitations & Future Work
## 12. GenAI Usage Declaration
## 13. Author
Shirui Zhao

University of Leeds

COMP Web Services and Web Data