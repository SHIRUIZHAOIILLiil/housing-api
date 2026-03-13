# Housing Market API
A FastAPI-based housing data and analytics service for official and user-contributed UK housing records.
## 1. Overview
This project implements a RESTful housing market API that provides structured access to 
UK housing-related data, including geographic reference data, official rental statistics, official property sales transactions, and user-contributed records. 
The service is designed as a data-oriented API rather than a simple database wrapper: 
in addition to standard resource retrieval, it supports filtering, aggregated statistics, availability queries, and selected trend visualisation endpoints.

The API combines authoritative public datasets with authenticated user-managed resources. 
Official datasets are exposed as read-oriented resources for search and analysis, 
while user-submitted rental and sales records can be created, updated, and deleted through protected endpoints using JWT bearer authentication. 
This separation helps preserve the integrity of official data while still supporting user contribution and experimentation.

## 2. Features
- **Reference geography lookup**  
  Supports area and postcode mapping resources for location-based queries.

- **Official housing data access**  
  Provides read-oriented access to official rental statistics and property sales transactions.

- **User-contributed records**  
  Allows authenticated users to create, update, and delete rental and sales records without modifying authoritative datasets.

- **Analytical API endpoints**  
  Supports filtered queries, aggregated statistics, latest snapshots, availability lookups, and selected trend visualisation endpoints.

- **JWT-based authentication**  
  Protects state-changing operations on user-managed resources using bearer-token authentication.

- **OpenAPI documentation**  
  Automatically generated interactive API documentation is available through FastAPI.
## 3. Tech Stack
- **Language:** Python 3.13
- **Web framework:** FastAPI
- **Database:** SQLite
- **Validation and schemas:** Pydantic
- **Authentication:** JWT / OAuth2 password bearer
- **API documentation:** OpenAPI / Swagger UI
- **Testing:** Pytest
- **ASGI server:** Uvicorn
- **Deployment:** Render
- **CI/CD:** GitHub Actions
## 4. Project Structure
The repository is organised into application code, data assets, tests, and supporting documentation:

```text
housing-api/
├── app/
│   ├── api/            # API dependencies and shared request handling utilities
│   ├── routers/        # FastAPI route definitions grouped by resource
│   ├── services/       # Business logic and database query functions
│   ├── schemas/        # Pydantic request/response models
│   ├── core/           # Configuration, authentication, and shared utilities
│   └── main.py         # FastAPI application entry point
├── data/               # SQLite database files and local data assets
├── tests/              # Automated pytest test suite
├── scripts/            # Database initialisation and utility scripts
├── docs/               # Additional project documentation
├── logs/               # Application or audit logs
├── openapi.json        # Exported OpenAPI specification
├── README.md           # Project overview and usage guide
└── requirements.txt    # Python dependencies
```
## 5. Setup & Installation
Clone the repository and install dependencies:

```bash
git clone https://github.com/SHIRUIZHAOIILLiil/housing-api.git
cd housing-api
pip install -r requirements.txt
```
Set the required environment variables before running the API:
```bash
export JWT_SECRET=your_secret_key
export HOST=127.0.0.1
export PORT=8000
```

If you want to use full dataset of the system, set environment variables:
```bash
export DATAPATH=/path/to/your/data
```
By default, the project uses the demo SQLite database. In config.py, both DATABASE and DATABASE_DEMO are defined, 
and get_conn() in deps.py is currently configured to connect to settings.DATABASE_DEMO. The demo database is intended for lightweight local testing and coursework demonstration, while the full database can be generated from raw source files when needed.


On Windows, use set in Command Prompt or $env:VARIABLE_NAME="value" in PowerShell instead of export.


## 6. Running the Project
Start the development server with:

```bash
uvicorn app.main:app --reload
```
By default, the API will be available at:
- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs for the interactive Swagger UI
- http://127.0.0.1:8000/redoc for the ReDoc interface

If you change HOST or PORT in your environment variables, use the corresponding address when accessing the API documentation.
## 7. Deployment
The API is deployed on Render and can be accessed online at:
```
- **Live API:** `https://housing-api-p0jk.onrender.com/`
- **Swagger UI:** `https://housing-api-p0jk.onrender.com/docs`
- **ReDoc:** `https://housing-api-p0jk.onrender.com/redoc`
```
The deployed version is intended for demonstration and inspection of the API. For local development, follow the setup instructions above and run the service with Uvicorn.

> The deployed service may take a short time to respond on first access due to Render cold starts.
## 8. API Overview

The API is organised into several resource families covering reference geography data, official housing datasets, user-managed records, and authentication.

### 8.1 Areas and Postcode Mapping

Reference endpoints for geographic lookup and postcode-to-area mapping.

- `GET /areas`
- `GET /areas/{area_code}`
- `GET /areas/{area_code}/postcodes`
- `GET /postcode_map`
- `GET /postcode_map/{postcode}`

### 8.2 Official Rental Statistics

Read-oriented endpoints for querying official rental statistics by area, postcode, time period, and related filters, including trend visualisation by area or area name.

- `GET /rent_stats_official/rent-stats`
- `GET /rent_stats_official/areas/{area_code}/rent-stats`
- `GET /rent_stats_official/areas/{area_code}/rent-stats/latest`
- `GET /rent_stats_official/areas/{area_code}/rent-stats/availability`
- `GET /rent_stats_official/areas/{area_code}/rent-trend.png`
- `GET /rent_stats_official/areas/rent-trend.png`

### 8.3 Official Sales Transactions

Read-oriented endpoints for official sales transaction lookup and aggregated sales statistics.

- `GET /sales_official`
- `GET /sales_official/transactions/{transaction_uuid}`
- `GET /sales_official/areas/{area_code}`
- `GET /sales_official/postcodes/{postcode}`
- `GET /sales_official/sales-stats`
- `GET /sales_official/areas/{area_code}/sales-stats`
- `GET /sales_official/areas/{area_code}/sales-stats/latest`
- `GET /sales_official/areas/{area_code}/sales-stats/availability`

### 8.4 User-Contributed Rental Records

Authenticated endpoints for creating, updating, and deleting user-managed rental records. Write operations require JWT bearer authentication.

- `GET /rent_user`
- `GET /rent_user/{record_id}`
- `POST /rent_user`
- `PUT /rent_user/{record_id}`
- `PATCH /rent_user/{record_id}`
- `DELETE /rent_user/{record_id}`

### 8.5 User-Contributed Sales Records

Authenticated endpoints for managing user-submitted sales transaction records. Write operations require JWT bearer authentication.

- `GET /user-sales-transactions`
- `GET /user-sales-transactions/{record_id}`
- `POST /user-sales-transactions`
- `PUT /user-sales-transactions/{record_id}`
- `PATCH /user-sales-transactions/{record_id}`
- `DELETE /user-sales-transactions/{record_id}`

### 8.6 Authentication

Authentication endpoints for user registration and login, used to obtain bearer tokens for protected write operations.

- `POST /auth/register`
- `POST /auth/login`
## 9. Usage

After starting the API locally or opening the deployed version, the easiest way to explore and test the service is through the interactive Swagger UI available at `/docs`.

A typical usage flow is:

1. Browse public read-only resources such as areas, postcode mapping, official rental statistics, and official sales transactions.
2. Use query parameters and resource-specific routes to filter by area, postcode, time period, or other supported fields.
3. Register a user account with `POST /auth/register` if you want to use protected write operations.
4. Log in with `POST /auth/login` to obtain a JWT bearer token.
5. Authorise in Swagger UI using the bearer token, then access protected endpoints for creating, updating, or deleting user-contributed rental and sales records.

The public official-data endpoints can be queried without authentication, while write operations on user-managed resources require a valid bearer token.
### Example workflow

- Look up an area or postcode
- Query official rental or sales data
- Register and log in
- Submit a user-contributed rental or sales record
## 10. Data Sources
- Housing Price: Statistical data set Price Paid Data
  - URL: https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads
- Renting Price: Price Index of Private Rents, UK: monthly price statistics
  - URL: https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/priceindexofprivaterentsukmonthlypricestatistics
- National Statistics Postcode Lookup
  - URL: https://geoportal.statistics.gov.uk/datasets/8a1d5b58df824b2e86fe07ddfdd87165/about 
## 11. Testing

The project includes an automated test suite built with `pytest` to verify core API behaviour, validation logic, and error handling.

To run the tests locally:

```bash
pytest
```
The test suite covers representative behaviours across the API, including:
successful requests to public read-only endpoints
validation of query parameters and path parameters
missing-resource behaviour such as 404 Not Found
invalid input cases such as 422 Unprocessable Entity
authenticated write operations for user-managed resources
Testing was used not only to check correctness, but also to improve consistency across endpoints, especially for validation, response codes, and protected operations.
## 12. Limitations and Future Work

The current implementation is suitable for coursework demonstration, but several limitations remain.

- The project currently uses SQLite, which is lightweight and portable but less suitable for higher write concurrency or larger-scale deployment.
- The security model supports JWT-based authentication for protected write operations, but more advanced controls such as role-based access control, token revocation, and rate limiting are not yet implemented.
- The contributed-data model currently focuses on authenticated end users and does not yet support richer uploader roles, moderation workflows, or trusted partner submissions.
- Although the API already provides filtering, aggregated statistics, availability queries, and trend visualisation, the analytical layer could be extended further with broader dataset coverage and richer machine-consumable outputs.

Future work would therefore focus on improving scalability, strengthening access control, extending the contributor model, and expanding the analytical capabilities of the API.
## 13. Generative AI Usage Declaration

Generative AI tools, primarily ChatGPT, were used during the project as support for planning, design discussion, testing strategy, debugging discussion, and documentation refinement.

AI was used to explore alternatives, clarify trade-offs, and improve the structure and wording of technical explanations, rather than to replace independent implementation work. 
All final code, design decisions, and written content were reviewed, adapted, and verified manually before inclusion in the project.

Examples of exported conversation logs are provided as supplementary material in line with the coursework requirements.

All generated suggestions were reviewed, tested and integrated manually.
## 14. API documentation PDF Reference
- Machine-readable OpenAPI specification: ```/docs/openapi_v2.json```
- Human-readable API documentation PDF: ```/docs/Housing-API.pdf```
## 15. Technical Report and Presentation Slide
- Technical Report: ```/docs/Housing-API-technical-report```
- Slides: ```/docs/Housing-API-slides.pdf``` or ```/docs/Housing-API.pptx```

## 16. Author
Shirui Zhao

University of Leeds

COMP3011 Web Services and Web Data