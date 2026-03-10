# housing-api

## 1. Overview
This project implements a RESTful Web API that provides analytical insights
into the UK housing market by integrating HM Land Registry(England and Wales) and ONS(UK) datasets.

The API supports full CRUD operations on housing transactions and locations,
and exposes additional analytical endpoints for regional price trends,
median prices, and affordability indicators.

The API supports:

- official housing statistics
- user-submitted rental and sales records
- authentication with JWT
- analytical endpoints for trends and aggregated metrics
## 2. Features
- RESTful API design following HTTP conventions
- Integration of UK housing datasets (ONS and HM Land Registry)
- Official housing statistics endpoints
- User-submitted rental and sales records (full CRUD)
- JWT-based authentication system
- Filtering and search capabilities
- Analytical endpoints for housing price trends
- Time-series rental statistics by area
- Postcode → area mapping
- Automated test suite using Pytest
- CI/CD pipeline with GitHub Actions
- Cloud deployment on Render
## 3. Tech Stack
- Language: Python 3.13
- Framework: FastAPI
- Database: Sqlite
- ORM SQLALchemy
- API Documentation: Swagger / OpenAPI
- Pydantic
- Pytest
- Uvicorn
- Render (deployment)
## 4. Project Structure
```
housing-api/
│
├── app/
│   ├── api/
│   │   ├── routers/        # API endpoints
│   │   └── deps.py         # shared dependencies
│   │
│   ├── security/           # JWT authentication
│   ├── services/           # business logic
│   ├── schemas/            # Pydantic models
│   └── main.py             # FastAPI application entry
│
├── tests/                  # pytest test suite
│
├── requirements.txt
├── README.md
└── .github/workflows       # CI pipeline
```

The project follows a layered architecture:

- Router layer → handles HTTP requests
- Service layer → contains business logic
- Schema layer → defines request and response models
- Security layer → manages authentication and authorization
## 5. Setup & Installation
Clone the repository:

```bash
https://github.com/SHIRUIZHAOIILLiil/housing-api.git
cd housing-api
pip install -r requirements.txt

Set environment variables:
export JWT_SECRET=your_secret_key
PORT=YOUR_PORT
HOST=YOUR_HOST

If you want to use full dataset of the system, set environment variables:
DATAPATH=Your_DATA_PATH
```
## 6. Running the Project
Start the FastAPI server:

```
uvicorn app.main:app --reload
http://HOST:PORT

Interactive API documentation:
http://HOST:PORT/docs
```
## 7. Deployment
```
The API is deployed on Render:
https://housing-api-p0jk.onrender.com/
Interactive API documentation:
https://housing-api-p0jk.onrender.com/docs#/
```
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
### 7.3 Official Rent Stats
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
### 7.5 User Rent Stats
- POST /rental-records 
  - Purpose: Create a new user-contributed rental record.
  - Responses:
    - 201 Created – successfully created
    - 400 Bad Request – invalid input (e.g. wrong time format)
    - 404 Not Found – area_code or postcode not found
- GET /rental-records/{id}
  - Purpose: Retrieve a specific rental record by ID.
  - Responses:
    - 200 OK – returns rental record
    - 404 Not Found – record not found
- GET /rental-records
  - Purpose: List user rental records (supports filtering by business time).
  - Responses:
    - 200 OK – returns list (possibly empty)
- PUT /rental-records/{id}
  - Purpose: Update a rental record.
  - Responses:
    - 200 OK – successfully updated
    - 400 Bad Request – invalid data
    - 404 Not Found – record not found
- DELETE /rental-records/{id}
  - Purpose: Delete a rental record.
  - Responses:
    - 204 No Content – successfully deleted
    - 404 Not Found – record not found
### 7.6 Rent Statistics
- GET /rent-stats
  - Purpose: Retrieve aggregated rent statistics for a given area and time period.
  - Responses:
    - 200 OK – returns statistics object
    - 404 Not Found – no data available
    - 400 Bad Request – missing or invalid parameters
- GET /areas/{area_code}/rent-stats
  - Purpose: Retrieve rent statistics time-series for a specific area.
  - Responses:
    - 200 OK – returns list (possibly empty)
    - 404 Not Found – area not found (optional)
- GET /areas/{area_code}/rent-stats
  - Purpose: Retrieve rent statistics time-series for a specific area.
  - Responses:
    - 200 OK – returns list (possibly empty)
    - 404 Not Found – area not found (optional)
### 7.7 User sales-transaction
- POST /user-sales-transactions
  - Purpose: Create a new user-contributed sales transaction record.
  - Request Body (JSON):
    - postcode (string, optional)
    - area_code (string, optional)
    - time_period (string, required, format YYYY-MM)
    - price (number, required)
    - property_type (string, optional, e.g. F, D, S, T)
    - tenure (string, optional)
    - new_build (boolean or string, optional)
  - Responses:
    - 201 Created – successfully created
    - 400 Bad Request – invalid input (e.g. wrong time format)
    - 404 Not Found – postcode or area_code not found
- GET /user-sales-transactions/{id}
  - Purpose: Retrieve a specific user sales transaction by ID.
  - Responses:
    - 200 OK – returns transaction object
    - 404 Not Found – transaction not found
- GET /user-sales-transactions
  - Purpose: List user sales transactions (supports filtering by business time).
  - Query Parameters (optional):
    - area_code
    - postcode
    - from (YYYY-MM)
    - to (YYYY-MM)
    - property_type
    - min_price
    - max_price
    - page
    - page_size
  - Responses:
    - 200 OK – returns list (possibly empty)
- PUT /user-sales-transactions/{id}
  - Purpose: Update a user sales transaction record.
  - Request Body (JSON):
    - Any updatable fields (e.g. price, property_type, tenure, etc.)
  - Responses:
    - 200 OK – successfully updated
    - 400 Bad Request – invalid data
    - 404 Not Found – transaction not found
- DELETE /user-sales-transactions/{id}
  - Purpose: Delete a user sales transaction record.
  - Responses:
    - 204 No Content – successfully deleted
    - 404 Not Found – transaction not found
## 8. Example Usage
## 9. Data Sources
- Housing Price: Statistical data set Price Paid Data
  - URL: https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads
- Renting Price: Price Index of Private Rents, UK: monthly price statistics
  - URL: https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/priceindexofprivaterentsukmonthlypricestatistics
- National Statistics Postcode Lookup
  - URL: https://geoportal.statistics.gov.uk/datasets/8a1d5b58df824b2e86fe07ddfdd87165/about 
## 10. Testing
This project includes an automated test suite built with Pytest.

Run tests with:

```bash
pytest
```
The test suite covers:
- API endpoints 
- CRUD operations 
- authentication 
- error handling
## 11. Limitations & Future Work
Current limitations include:

- SQLite limits scalability for large datasets
- limited caching for analytical queries
- basic authentication without role-based access control

Future improvements may include:

- migration to PostgreSQL
- caching for frequently accessed analytics
- advanced authentication and user roles
## 12. GenAI Usage Declaration
Generative AI tools (ChatGPT) were used to assist with:

- debugging Python and FastAPI errors
- improving API documentation structure
- reviewing database design
- generating test case ideas

All generated suggestions were reviewed, tested and integrated manually.
## 13. Author
Shirui Zhao

University of Leeds

COMP3011 Web Services and Web Data