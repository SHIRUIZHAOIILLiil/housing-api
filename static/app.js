const $ = (id) => document.getElementById(id);

const output = $("output");
const statusBadge = $("statusBadge");
const responseSummary = $("responseSummary");
const preview = $("preview");
const resultPanel = $("resultPanel");
const imagePreviewWrap = $("imagePreviewWrap");
const imagePreview = $("imagePreview");
const structuredOutput = $("structuredOutput");

function hideImagePreview() {
  imagePreviewWrap.style.display = "none";
  imagePreview.removeAttribute("src");
}

function showImagePreview(url) {
  imagePreview.src = url;
  imagePreviewWrap.style.display = "block";
}

function setStatus(text, type = "info") {
  statusBadge.textContent = text;
  statusBadge.className = `status-badge ${type}`;
}

function setSummary(text) {
  responseSummary.textContent = text;
}

function scrollToResults() {
  if (window.innerWidth < 1100) {
    resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}
function showOutput(data) {
  output.textContent =
    typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function renderPreview(payload) {
  preview.innerHTML = `<h3>Quick Preview</h3>`;

  if (payload.error) {
    preview.innerHTML += `
      <div class="item">
        <span class="label">Error:</span>
        <span class="value">${payload.error}</span>
      </div>
    `;
    return;
  }

  const response = payload.response || {};
  const body = response.body;

  preview.innerHTML += `
    <div class="item">
      <span class="label">HTTP Status:</span>
      <span class="value">${response.status ?? "N/A"}</span>
    </div>
  `;

  if (body === null || body === undefined) {
    preview.innerHTML += `
      <div class="item">
        <span class="label">Result:</span>
        <span class="value">No body returned</span>
      </div>
    `;
    return;
  }

  if (Array.isArray(body)) {
    preview.innerHTML += `
      <div class="item">
        <span class="label">Result Type:</span>
        <span class="value">Array (${body.length} items)</span>
      </div>
    `;

    body.slice(0, 3).forEach((item, index) => {
      preview.innerHTML += `
        <div class="item">
          <span class="label">Item ${index + 1}:</span>
          <span class="value">${summariseObject(item)}</span>
        </div>
      `;
    });
    return;
  }

  if (typeof body === "object") {
    const keys = Object.keys(body);
    preview.innerHTML += `
      <div class="item">
        <span class="label">Fields:</span>
        <span class="value">${keys.join(", ") || "None"}</span>
      </div>
    `;

    keys.slice(0, 6).forEach((key) => {
      preview.innerHTML += `
        <div class="item">
          <span class="label">${key}:</span>
          <span class="value">${formatValue(body[key])}</span>
        </div>
      `;
    });
    return;
  }

  preview.innerHTML += `
    <div class="item">
      <span class="label">Result:</span>
      <span class="value">${String(body)}</span>
    </div>
  `;
}

function resetRenderedViews() {
  hideImagePreview();
  hideStructuredOutput();
}

function summariseObject(obj) {
  if (!obj || typeof obj !== "object") return String(obj);

  const priorityKeys = [
    "id",
    "area_code",
    "postcode",
    "time_period",
    "rent",
    "price",
    "name",
    "label"
  ];

  const parts = [];

  priorityKeys.forEach((key) => {
    if (obj[key] !== undefined && obj[key] !== null) {
      parts.push(`${key}: ${obj[key]}`);
    }
  });

  if (parts.length === 0) {
    const fallbackKeys = Object.keys(obj).slice(0, 4);
    fallbackKeys.forEach((key) => {
      parts.push(`${key}: ${formatValue(obj[key])}`);
    });
  }

  return parts.join(" | ");
}

function formatValue(value) {
  if (value === null) return "null";
  if (value === undefined) return "undefined";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normaliseValue(value) {
  if (value === null) return "null";
  if (value === undefined) return "undefined";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function hideStructuredOutput() {
  structuredOutput.style.display = "none";
  structuredOutput.innerHTML = "";
}

function showStructuredOutput() {
  structuredOutput.style.display = "block";
}

function renderEmptyStructuredOutput(message = "No structured output available.") {
  showStructuredOutput();
  structuredOutput.innerHTML = `
    <h3>Structured View</h3>
    <div class="empty-state">${escapeHtml(message)}</div>
  `;
}

function renderObjectAsCards(obj, title = "Structured View") {
  const entries = Object.entries(obj || {});

  if (entries.length === 0) {
    renderEmptyStructuredOutput("Object is empty.");
    return;
  }

  const simpleEntries = [];
  const complexEntries = [];

  entries.forEach(([key, value]) => {
    if (
      value === null ||
      ["string", "number", "boolean"].includes(typeof value)
    ) {
      simpleEntries.push([key, value]);
    } else {
      complexEntries.push([key, value]);
    }
  });

  showStructuredOutput();

  let html = `<h3>${escapeHtml(title)}</h3>`;

  if (simpleEntries.length > 0) {
    html += `<div class="kv-grid">`;
    simpleEntries.forEach(([key, value]) => {
      html += `
        <div class="kv-card">
          <div class="kv-key">${escapeHtml(key)}</div>
          <div class="kv-value">${escapeHtml(normaliseValue(value))}</div>
        </div>
      `;
    });
    html += `</div>`;
  }

  if (complexEntries.length > 0) {
    complexEntries.forEach(([key, value]) => {
      html += `
        <div class="nested-json">
          <strong>${escapeHtml(key)}</strong>
          <pre>${escapeHtml(JSON.stringify(value, null, 2))}</pre>
        </div>
      `;
    });
  }

  structuredOutput.innerHTML = html;
}

function collectColumnsFromArray(items) {
  const seen = new Set();
  const columns = [];

  items.forEach((item) => {
    if (item && typeof item === "object" && !Array.isArray(item)) {
      Object.keys(item).forEach((key) => {
        if (!seen.has(key)) {
          seen.add(key);
          columns.push(key);
        }
      });
    }
  });

  const preferredOrder = [
    "id",
    "name",
    "label",
    "area_code",
    "area_name",
    "postcode",
    "time_period",
    "from",
    "to",
    "rent",
    "price",
    "property_type",
    "bedrooms",
    "source",
    "created_at",
    "updated_at"
  ];

  columns.sort((a, b) => {
    const ia = preferredOrder.indexOf(a);
    const ib = preferredOrder.indexOf(b);

    if (ia === -1 && ib === -1) return a.localeCompare(b);
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });

  return columns;
}

function getOfficialSalesTransactionFilters() {
  return {
    date_from: $("officialSalesDateFrom").value.trim(),
    date_to: $("officialSalesDateTo").value.trim(),
    min_price: $("officialSalesMinPrice").value.trim(),
    max_price: $("officialSalesMaxPrice").value.trim(),
    property_type: $("officialSalesPropertyType").value,
    new_build: $("officialSalesNewBuild").value,
    tenure: $("officialSalesTenure").value,
    limit: $("officialSalesLimit").value.trim(),
    offset: $("officialSalesOffset").value.trim(),
    sort_by: $("officialSalesSortBy").value,
    order: $("officialSalesOrder").value,
    include_total: $("officialSalesIncludeTotal").value
  };
}


function renderArrayAsTable(items, title = "Structured View") {
  if (!Array.isArray(items) || items.length === 0) {
    renderEmptyStructuredOutput("No rows returned.");
    return;
  }

  const objectRows = items.filter(
    (item) => item && typeof item === "object" && !Array.isArray(item)
  );

  if (objectRows.length !== items.length) {
    showStructuredOutput();
    structuredOutput.innerHTML = `
      <h3>${escapeHtml(title)}</h3>
      <div class="nested-json">${escapeHtml(JSON.stringify(items, null, 2))}</div>
    `;
    return;
  }

  const columns = collectColumnsFromArray(objectRows);

  let html = `<h3>${escapeHtml(title)}</h3>`;
  html += `<div class="table-wrap"><table class="result-table"><thead><tr>`;

  columns.forEach((col) => {
    html += `<th>${escapeHtml(col)}</th>`;
  });

  html += `</tr></thead><tbody>`;

  objectRows.forEach((row) => {
    html += `<tr>`;
    columns.forEach((col) => {
      const value = row[col];
      html += `<td>${escapeHtml(normaliseValue(value))}</td>`;
    });
    html += `</tr>`;
  });

  html += `</tbody></table></div>`;
  html += `<div class="result-note">${objectRows.length} row(s) returned.</div>`;

  showStructuredOutput();
  structuredOutput.innerHTML = html;
}

function inferStructuredTitle(payload) {
  const url = payload?.request?.url || "";

  if (url.includes("/areas?") || url.endsWith("/areas")) return "Area Results";
  if (url.includes("/postcode_map?") || url.endsWith("/postcode_map")) return "Postcode Results";
  if (url.includes("/rent_user")) return "User Rent Results";
  if (url.includes("/user-sales-transactions")) return "User Sales Results";
  if (url.includes("/sales_official")) return "Official Sales Results";
  if (url.includes("/rent_stats_official")) return "Official Rent Results";
  if (url.includes("/auth/")) return "Authentication Result";

  return "Structured View";
}

function renderStructuredBody(payload) {
  const body = payload?.response?.body;
  const title = inferStructuredTitle(payload);

  if (body === null || body === undefined) {
    renderEmptyStructuredOutput("No response body returned.");
    return;
  }

  if (Array.isArray(body)) {
    renderArrayAsTable(body, title);
    return;
  }

  if (typeof body === "object") {
    const candidateArrayKeys = ["items", "results", "data", "records", "rows"];

    for (const key of candidateArrayKeys) {
      if (Array.isArray(body[key])) {
        renderArrayAsTable(body[key], title);
        return;
      }
    }

    renderObjectAsCards(body, title);
    return;
  }

  showStructuredOutput();
  structuredOutput.innerHTML = `
    <h3>${escapeHtml(title)}</h3>
    <div class="empty-state">${escapeHtml(String(body))}</div>
  `;
}

function getBaseUrl() {
  return $("baseUrl").value.trim().replace(/\/+$/, "");
}

function getToken() {
  return $("token").value.trim();
}

function getJsonHeaders(withAuth = false) {
  const headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
  };

  if (withAuth && getToken()) {
    headers["Authorization"] = `Bearer ${getToken()}`;
  }

  return headers;
}

function buildQuery(params) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      searchParams.append(key, value);
    }
  });

  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

async function apiRequest(path, options = {}, actionLabel = "Request") {
  const url = `${getBaseUrl()}${path}`;

  setStatus("Loading...", "loading");
  setSummary(`${actionLabel} in progress...`);
  scrollToResults();

  resetRenderedViews();

  try {
    const response = await fetch(url, options);

    const contentType = response.headers.get("content-type") || "";
    let body;

    if (response.status === 204) {
      body = null;
    } else if (contentType.includes("application/json")) {
      body = await response.json();
    } else {
      body = await response.text();
    }

    const payload = {
      request: {
        method: options.method || "GET",
        url,
        headers: options.headers || {}
      },
      response: {
        status: response.status,
        ok: response.ok,
        body
      }
    };

    showOutput(payload);
    renderPreview(payload);
    renderStructuredBody(payload);

    if (response.ok) {
      setStatus(`HTTP ${response.status}`, "success");
      setSummary(`${actionLabel} completed successfully.`);
    } else {
      setStatus(`HTTP ${response.status}`, "error");
      setSummary(`${actionLabel} returned an error response.`);
    }

    return { response, body };
  } catch (error) {
    const payload = { error: error.message };
    showOutput(payload);
    renderPreview(payload);
    setStatus("Request Failed", "error");
    setSummary(`${actionLabel} failed before receiving a response.`);
    scrollToResults();
    throw error;
  }
}

function saveConfig() {
  localStorage.setItem("housing_api_base_url", $("baseUrl").value.trim());
  localStorage.setItem("housing_api_token", $("token").value.trim());
}

function loadConfig() {
  const savedBaseUrl = localStorage.getItem("housing_api_base_url");
  const savedToken = localStorage.getItem("housing_api_token");

  if (savedBaseUrl) $("baseUrl").value = savedBaseUrl;
  if (savedToken) $("token").value = savedToken;
}

async function imageRequest(path, actionLabel = "Image Request") {
  const url = `${getBaseUrl()}${path}`;
  resetRenderedViews();
  setStatus("Loading...", "loading");
  setSummary(`${actionLabel} in progress...`);
  scrollToResults();

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: { "Accept": "image/png" }
    });

    if (!response.ok) {
      let errorBody;
      const contentType = response.headers.get("content-type") || "";

      if (contentType.includes("application/json")) {
        errorBody = await response.json();
      } else {
        errorBody = await response.text();
      }

      const payload = {
        request: { method: "GET", url },
        response: {
          status: response.status,
          ok: false,
          body: errorBody
        }
      };

      hideImagePreview();
      showOutput(payload);
      renderPreview(payload);
      setStatus(`HTTP ${response.status}`, "error");
      setSummary(`${actionLabel} returned an error response.`);
      return;
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);

    showImagePreview(objectUrl);

    const payload = {
      request: { method: "GET", url },
      response: {
        status: response.status,
        ok: true,
        body: "PNG image returned successfully"
      }
    };

    showOutput(payload);
    renderPreview(payload);
    renderObjectAsCards(
  {
    message: "PNG image returned successfully",
    endpoint: path,
    status: response.status
  },
  "Image Result"
);
    setStatus(`HTTP ${response.status}`, "success");
    setSummary(`${actionLabel} completed successfully.`);
  } catch (error) {
    hideImagePreview();
    const payload = { error: error.message };
    showOutput(payload);
    renderPreview(payload);
    setStatus("Request Failed", "error");
    setSummary(`${actionLabel} failed before receiving a response.`);
    throw error;
  }
}

$("saveConfigBtn").addEventListener("click", () => {
  saveConfig();
  setStatus("Config Saved", "success");
  setSummary("Base URL and token saved locally.");
  renderPreview({
    response: { status: "-", body: { message: "Configuration saved" } }
  });
  showOutput("Base URL and token saved.");
  scrollToResults();
});

$("clearTokenBtn").addEventListener("click", () => {
  $("token").value = "";
  saveConfig();
  setStatus("Token Cleared", "success");
  setSummary("Stored token has been cleared.");
  renderPreview({
    response: { status: "-", body: { message: "Token cleared" } }
  });
  showOutput("Stored token cleared.");
  scrollToResults();
});

$("registerBtn").addEventListener("click", async () => {
  const payload = {
    username: $("registerUsername").value.trim(),
    email: $("registerEmail").value.trim(),
    password: $("registerPassword").value.trim()
  };

  await apiRequest(
    "/auth/register",
    {
      method: "POST",
      headers: getJsonHeaders(false),
      body: JSON.stringify(payload)
    },
    "User registration"
  );
});

$("loginBtn").addEventListener("click", async () => {
  const formData = new URLSearchParams();
  formData.append("username", $("loginUsername").value.trim());
  formData.append("password", $("loginPassword").value.trim());

  const { response, body } = await apiRequest(
    "/auth/login",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
      },
      body: formData.toString()
    },
    "User login"
  );

  if (response.ok && body?.access_token) {
    $("token").value = body.access_token;
    saveConfig();
    setStatus("Login Success", "success");
    setSummary("Token received and stored locally.");
  }
});

$("getAreaBtn").addEventListener("click", async () => {
  const areaCode = $("areaCode").value.trim();
  await apiRequest(
    `/areas/${encodeURIComponent(areaCode)}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get area by code"
  );
});

$("searchAreasBtn").addEventListener("click", async () => {
  const qs = buildQuery({
    q: $("areaQuery").value.trim(),
    limit: $("areaLimit").value.trim()
  });

  await apiRequest(
    `/areas${qs}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Search areas"
  );
});

$("postcodeExactBtn").addEventListener("click", async () => {
  const postcode = $("postcodeExact").value.trim();
  await apiRequest(
    `/postcode_map/${encodeURIComponent(postcode)}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get postcode mapping"
  );
});

$("postcodeSearchBtn").addEventListener("click", async () => {
  const qs = buildQuery({
    q: $("postcodeQuery").value.trim(),
    limit: $("postcodeLimit").value.trim()
  });

  await apiRequest(
    `/postcode_map${qs}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Search postcodes"
  );
});

$("rentPointBtn").addEventListener("click", async () => {
  const qs = buildQuery({
    area_code: $("rentAreaCode").value.trim(),
    time_period: $("rentTimePeriod").value.trim()
  });

  await apiRequest(
    `/rent_stats_official/rent-stats${qs}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get rent point stats"
  );
});

$("rentSeriesBtn").addEventListener("click", async () => {
  const areaCode = $("rentAreaCode").value.trim();
  const qs = buildQuery({
    from: $("rentFrom").value.trim(),
    to: $("rentTo").value.trim()
  });

  await apiRequest(
    `/rent_stats_official/areas/${encodeURIComponent(areaCode)}/rent-stats${qs}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get rent time series"
  );
});

$("rentLatestBtn").addEventListener("click", async () => {
  const areaCode = $("rentAreaCode").value.trim();

  await apiRequest(
    `/rent_stats_official/areas/${encodeURIComponent(areaCode)}/rent-stats/latest`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get latest rent stats"
  );
});

$("rentAvailabilityBtn").addEventListener("click", async () => {
  const areaCode = $("rentAreaCode").value.trim();

  await apiRequest(
    `/rent_stats_official/areas/${encodeURIComponent(areaCode)}/rent-stats/availability`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get rent availability"
  );
});

function getSalesFilters() {
  return {
    property_type: $("salesPropertyType").value,
    new_build: $("salesNewBuild").value,
    tenure: $("salesTenure").value
  };
}

$("salesPointBtn").addEventListener("click", async () => {
  const areaCode = $("salesAreaCode").value.trim();
  const timePeriod = $("salesTimePeriod").value.trim();

  if (!areaCode || !timePeriod) {
    setStatus("Missing Required Fields", "error");
    setSummary("Official sales point stats require both area code and time period.");
    renderEmptyStructuredOutput("Please enter both area code and time period.");
    return;
  }

  const qs = buildQuery({
    area_code: areaCode,
    time_period: timePeriod,
    ...getSalesFilters()
  });

  await apiRequest(
    `/sales_official/sales-stats${qs}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get sales point stats"
  );
});

$("salesSeriesBtn").addEventListener("click", async () => {
  const areaCode = $("salesAreaCode").value.trim();
  const qs = buildQuery({
    date_from: $("salesDateFrom").value.trim(),
    date_to: $("salesDateTo").value.trim(),
    ...getSalesFilters()
  });

  await apiRequest(
    `/sales_official/areas/${encodeURIComponent(areaCode)}/sales-stats${qs}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get sales time series"
  );
});

$("salesLatestBtn").addEventListener("click", async () => {
  const areaCode = $("salesAreaCode").value.trim();
  const qs = buildQuery({
    ...getSalesFilters()
  });

  await apiRequest(
    `/sales_official/areas/${encodeURIComponent(areaCode)}/sales-stats/latest${qs}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get latest sales stats"
  );
});

$("salesAvailabilityBtn").addEventListener("click", async () => {
  const areaCode = $("salesAreaCode").value.trim();

  await apiRequest(
    `/sales_official/areas/${encodeURIComponent(areaCode)}/sales-stats/availability`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get sales availability"
  );
});

$("createRentRecordBtn").addEventListener("click", async () => {
  const payload = {
    postcode: $("userRentPostcode").value.trim(),
    time_period: $("userRentTimePeriod").value.trim(),
    rent: $("userRentValue").value ? Number($("userRentValue").value) : null,
    area_code: $("userRentAreaCode").value.trim() || null,
    bedrooms: $("userRentBedrooms").value ? Number($("userRentBedrooms").value) : null,
    property_type: $("userRentPropertyType").value || null,
    source: $("userRentSource").value
  };

  await apiRequest(
    "/rent_user",
    {
      method: "POST",
      headers: getJsonHeaders(true),
      body: JSON.stringify(payload)
    },
    "Create user rent record"
  );
});

$("listRentRecordsBtn").addEventListener("click", async () => {
  const qs = buildQuery({
    area_code: $("listRentAreaCode").value.trim(),
    time_period: $("listRentTimePeriod").value.trim(),
    limit: $("listRentLimit").value.trim()
  });

  await apiRequest(
    `/rent_user${qs}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "List user rent records"
  );
});

$("getRentRecordBtn").addEventListener("click", async () => {
  const recordId = $("rentRecordId").value.trim();

  await apiRequest(
    `/rent_user/${encodeURIComponent(recordId)}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get one rent record"
  );
});

$("putRentRecordBtn").addEventListener("click", async () => {
  const recordId = $("rentRecordId").value.trim();

  const payload = {
    postcode: $("userRentPostcode").value.trim(),
    time_period: $("userRentTimePeriod").value.trim(),
    rent: $("userRentValue").value ? Number($("userRentValue").value) : null,
    area_code: $("userRentAreaCode").value.trim() || null,
    bedrooms: $("userRentBedrooms").value ? Number($("userRentBedrooms").value) : null,
    property_type: $("userRentPropertyType").value || null,
    source: $("userRentSource").value
  };

  await apiRequest(
    `/rent_user/${encodeURIComponent(recordId)}`,
    {
      method: "PUT",
      headers: getJsonHeaders(true),
      body: JSON.stringify(payload)
    },
    "Replace rent record"
  );
});

$("patchRentRecordBtn").addEventListener("click", async () => {
  const recordId = $("rentRecordId").value.trim();

  const payload = {};

  if ($("userRentPostcode").value.trim()) {
    payload.postcode = $("userRentPostcode").value.trim();
  }
  if ($("userRentAreaCode").value.trim()) {
    payload.area_code = $("userRentAreaCode").value.trim();
  }
  if ($("userRentTimePeriod").value.trim()) {
    payload.time_period = $("userRentTimePeriod").value.trim();
  }
  if ($("userRentValue").value.trim()) {
    payload.rent = Number($("userRentValue").value);
  }
  if ($("userRentBedrooms").value.trim()) {
    payload.bedrooms = Number($("userRentBedrooms").value);
  }
  if ($("userRentPropertyType").value) {
    payload.property_type = $("userRentPropertyType").value;
  }
  if ($("userRentSource").value) {
    payload.source = $("userRentSource").value;
  }

  await apiRequest(
    `/rent_user/${encodeURIComponent(recordId)}`,
    {
      method: "PATCH",
      headers: getJsonHeaders(true),
      body: JSON.stringify(payload)
    },
    "Patch rent record"
  );
});

$("deleteRentRecordBtn").addEventListener("click", async () => {
  const recordId = $("rentRecordId").value.trim();

  await apiRequest(
    `/rent_user/${encodeURIComponent(recordId)}`,
    {
      method: "DELETE",
      headers: {
        "Accept": "application/json",
        ...(getToken() ? { "Authorization": `Bearer ${getToken()}` } : {})
      }
    },
    "Delete rent record"
  );
});

$("createSaleRecordBtn").addEventListener("click", async () => {
  const payload = {
    postcode: $("userSalePostcode").value.trim(),
    time_period: $("userSaleTimePeriod").value.trim(),
    price: $("userSalePrice").value ? Number($("userSalePrice").value) : null,
    area_code: $("userSaleAreaCode").value.trim() || null,
    property_type: $("userSalePropertyType").value || null,
    source: $("userSaleSource").value
  };

  await apiRequest(
    "/user-sales-transactions",
    {
      method: "POST",
      headers: getJsonHeaders(true),
      body: JSON.stringify(payload)
    },
    "Create user sales transaction"
  );
});

$("listSaleRecordsBtn").addEventListener("click", async () => {
  const qs = buildQuery({
    postcode: $("listSalePostcode").value.trim(),
    area_code: $("listSaleAreaCode").value.trim(),
    from_period: $("listSaleFromPeriod").value.trim(),
    to_period: $("listSaleToPeriod").value.trim(),
    property_type: $("listSalePropertyType").value,
    limit: $("listSaleLimit").value.trim()
  });

  await apiRequest(
    `/user-sales-transactions${qs}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "List user sales transactions"
  );
});

$("getSaleRecordBtn").addEventListener("click", async () => {
  const recordId = $("saleRecordId").value.trim();

  await apiRequest(
    `/user-sales-transactions/${encodeURIComponent(recordId)}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get one sales transaction"
  );
});

$("deleteSaleRecordBtn").addEventListener("click", async () => {
  const recordId = $("saleRecordId").value.trim();

  await apiRequest(
    `/user-sales-transactions/${encodeURIComponent(recordId)}`,
    {
      method: "DELETE",
      headers: {
        "Accept": "application/json",
        ...(getToken() ? { "Authorization": `Bearer ${getToken()}` } : {})
      }
    },
    "Delete sales transaction"
  );
});

$("putSaleRecordBtn").addEventListener("click", async () => {
  const recordId = $("saleRecordId").value.trim();

  const payload = {
    postcode: $("userSalePostcode").value.trim(),
    time_period: $("userSaleTimePeriod").value.trim(),
    price: $("userSalePrice").value ? Number($("userSalePrice").value) : null,
    area_code: $("userSaleAreaCode").value.trim() || null,
    property_type: $("userSalePropertyType").value || null,
    source: $("userSaleSource").value
  };

  await apiRequest(
    `/user-sales-transactions/${encodeURIComponent(recordId)}`,
    {
      method: "PUT",
      headers: getJsonHeaders(true),
      body: JSON.stringify(payload)
    },
    "Replace sales transaction"
  );
});

$("patchSaleRecordBtn").addEventListener("click", async () => {
  const recordId = $("saleRecordId").value.trim();

  const payload = {};

  if ($("userSalePostcode").value.trim()) payload.postcode = $("userSalePostcode").value.trim();
  if ($("userSaleAreaCode").value.trim()) payload.area_code = $("userSaleAreaCode").value.trim();
  if ($("userSaleTimePeriod").value.trim()) payload.time_period = $("userSaleTimePeriod").value.trim();
  if ($("userSalePrice").value.trim()) payload.price = Number($("userSalePrice").value);
  if ($("userSalePropertyType").value) payload.property_type = $("userSalePropertyType").value;
  if ($("userSaleSource").value) payload.source = $("userSaleSource").value;

  await apiRequest(
    `/user-sales-transactions/${encodeURIComponent(recordId)}`,
    {
      method: "PATCH",
      headers: getJsonHeaders(true),
      body: JSON.stringify(payload)
    },
    "Patch sales transaction"
  );
});

$("rentTrendByCodeBtn").addEventListener("click", async () => {
  const areaCode = $("rentAreaCode").value.trim();

  const qs = buildQuery({
    from: $("rentFrom").value.trim(),
    to: $("rentTo").value.trim(),
    metric: $("rentMetric").value,
    bedrooms: $("rentBedroomsTrend").value
  });

  await imageRequest(
    `/rent_stats_official/areas/${encodeURIComponent(areaCode)}/rent-trend.png${qs}`,
    "Get rent trend PNG by area code"
  );
});

$("rentTrendByNameBtn").addEventListener("click", async () => {
  const qs = buildQuery({
    area: $("rentAreaNameTrend").value.trim(),
    from: $("rentFrom").value.trim(),
    to: $("rentTo").value.trim(),
    metric: $("rentMetric").value,
    bedrooms: $("rentBedroomsTrend").value
  });

  await imageRequest(
    `/rent_stats_official/areas/rent-trend.png${qs}`,
    "Get rent trend PNG by area name"
  );
});
$("officialSalesByAreaBtn").addEventListener("click", async () => {
  const areaCode = $("officialSalesAreaCode").value.trim();

  if (!areaCode) {
    setStatus("Missing Required Fields", "error");
    setSummary("Listing official sales by area requires area code.");
    renderEmptyStructuredOutput("Please enter an area code.");
    return;
  }

  const qs = buildQuery(getOfficialSalesTransactionFilters());

  await apiRequest(
    `/sales_official/areas/${encodeURIComponent(areaCode)}${qs}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "List official sales transactions by area"
  );
});

$("officialSalesByPostcodeBtn").addEventListener("click", async () => {
  const postcode = $("officialSalesPostcode").value.trim();

  if (!postcode) {
    setStatus("Missing Required Fields", "error");
    setSummary("Listing official sales by postcode requires postcode.");
    renderEmptyStructuredOutput("Please enter a postcode.");
    return;
  }

  const qs = buildQuery(getOfficialSalesTransactionFilters());

  await apiRequest(
    `/sales_official/postcodes/${encodeURIComponent(postcode)}${qs}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "List official sales transactions by postcode"
  );
});

$("officialSalesByUuidBtn").addEventListener("click", async () => {
  const transactionUuid = $("officialSalesUuid").value.trim();

  if (!transactionUuid) {
    setStatus("Missing Required Fields", "error");
    setSummary("Getting one official sales transaction requires a UUID.");
    renderEmptyStructuredOutput("Please enter a transaction UUID.");
    return;
  }

  await apiRequest(
    `/sales_official/transactions/${encodeURIComponent(transactionUuid)}`,
    {
      method: "GET",
      headers: { "Accept": "application/json" }
    },
    "Get official sales transaction by UUID"
  );
});

loadConfig();
setStatus("Ready", "info");
setSummary("Choose an action to begin.");
