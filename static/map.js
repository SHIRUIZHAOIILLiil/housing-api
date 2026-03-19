const $ = (id) => document.getElementById(id);

const gbpFormatter = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
  maximumFractionDigits: 0
});

const decimalFormatter = new Intl.NumberFormat("en-GB", {
  maximumFractionDigits: 1
});

const RENT_EXPLORER_SERIES_COLORS = ["#2563eb", "#0f766e", "#d97706", "#dc2626"];
const RENT_EXPLORER_MAX_SELECTION = 4;
const RENT_EXPLORER_MAP_MIN_ZOOM = 1;
const RENT_EXPLORER_MAP_MAX_ZOOM = 10;
const RENT_EXPLORER_MAP_ZOOM_STEP = 1.6;
const RENT_EXPLORER_LABEL_ZOOM_THRESHOLD = 1.65;
const RENT_EXPLORER_LABEL_LIMIT = 120;
const RENT_EXPLORER_MAP_DRAG_THRESHOLD = 4;
const RENT_EXPLORER_MAP_VIEWBOX = {
  width: 760,
  height: 620,
  padding: 24
};

const rentExplorerState = {
  summary: null,
  selectedAreaCodes: [],
  focusedAreaCode: null,
  boundaryGeoJson: null,
  boundaryFeaturesByCode: new Map(),
  boundaryLoadPromise: null,
  boundaryProjection: null,
  lastSummaryRangeKey: null,
  mapZoom: RENT_EXPLORER_MAP_MIN_ZOOM,
  mapPanX: 0,
  mapPanY: 0,
  mapInteractionsBound: false,
  mapDragPointerId: null,
  mapDragActive: false,
  mapDragLastClientX: 0,
  mapDragLastClientY: 0,
  mapDragStartClientX: 0,
  mapDragStartClientY: 0,
  mapDragMoved: false,
  suppressNextRegionClick: false
};

function getDefaultBaseUrl() {
  return window.location.origin || "http://127.0.0.1:8000";
}

function getBaseUrl() {
  return $("mapBaseUrl").value.trim().replace(/\/+$/, "") || getDefaultBaseUrl();
}

function saveConfig() {
  localStorage.setItem("housing_api_base_url", getBaseUrl());
}

function loadConfig() {
  $("mapBaseUrl").value =
    localStorage.getItem("housing_api_base_url") ||
    getDefaultBaseUrl();
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

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchJsonData(path, options = {}) {
  const url = `${getBaseUrl()}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Accept": "application/json",
      ...(options.headers || {})
    }
  });

  const contentType = response.headers.get("content-type") || "";
  let body = null;

  if (response.status !== 204) {
    body = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
  }

  if (!response.ok) {
    const message =
      typeof body === "string"
        ? body
        : body?.detail || `HTTP ${response.status}`;
    throw new Error(message);
  }

  return body;
}

function setRentExplorerMessage(text, type = "info") {
  const message = $("rentExplorerMessage");
  message.textContent = text;
  message.className = `explorer-message ${type}`;
}

function getRentExplorerMetricLabel(metric) {
  if (metric === "rental_price") return "Rental Price";
  if (metric === "annual_change") return "Annual Change";
  return "Index Value";
}

function formatRentExplorerValue(metric, value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "N/A";
  }

  const numericValue = Number(value);

  if (metric === "rental_price") {
    return gbpFormatter.format(numericValue);
  }

  if (metric === "annual_change") {
    const prefix = numericValue > 0 ? "+" : "";
    return `${prefix}${decimalFormatter.format(numericValue)}%`;
  }

  return decimalFormatter.format(numericValue);
}

function formatRentExplorerAxisValue(metric, value) {
  if (metric === "rental_price") {
    return `GBP ${Math.round(value)}`;
  }

  if (metric === "annual_change") {
    return `${value > 0 ? "+" : ""}${decimalFormatter.format(value)}%`;
  }

  return decimalFormatter.format(value);
}

function getRentExplorerMetric() {
  return $("rentExplorerMetric").value;
}

function getRentExplorerBedrooms() {
  return $("rentExplorerBedrooms").value;
}

function syncRentExplorerBedrooms() {
  const metric = getRentExplorerMetric();
  const bedroomsSelect = $("rentExplorerBedrooms");

  Array.from(bedroomsSelect.options).forEach((option) => {
    option.disabled = metric === "annual_change" && option.value !== "overall";
  });

  if (metric === "annual_change") {
    bedroomsSelect.value = "overall";
  }
}

function getGeoJsonPath() {
  return $("rentMapSvg").dataset.geojsonPath;
}

function projectLngLatPoint(lng, lat) {
  const lambda = (lng * Math.PI) / 180;
  const phi = Math.max(Math.min(lat, 89.5), -89.5) * (Math.PI / 180);
  return {
    x: lambda,
    y: Math.log(Math.tan(Math.PI / 4 + phi / 2))
  };
}

function detectBoundaryCoordinateMode(geoJson) {
  const crsName = String(geoJson?.crs?.properties?.name || "").toUpperCase();

  if (crsName.includes("27700")) {
    return "projected";
  }

  if (crsName.includes("4326") || crsName.includes("CRS84") || crsName.includes("WGS84")) {
    return "lnglat";
  }

  let sampleCoordinate = null;

  for (const feature of geoJson?.features || []) {
    walkGeometryCoordinates(feature.geometry, (coordinate) => {
      if (!sampleCoordinate) {
        sampleCoordinate = coordinate;
      }
    });

    if (sampleCoordinate) {
      break;
    }
  }

  if (!sampleCoordinate) {
    return "lnglat";
  }

  const [x, y] = sampleCoordinate;
  return Math.abs(x) > 180 || Math.abs(y) > 90 ? "projected" : "lnglat";
}

function normaliseBoundaryCoordinate(mode, x, y) {
  if (mode === "lnglat") {
    return projectLngLatPoint(x, y);
  }

  return { x, y };
}

function walkGeometryCoordinates(geometry, callback) {
  if (!geometry) return;

  const polygonGroups =
    geometry.type === "Polygon"
      ? [geometry.coordinates]
      : geometry.type === "MultiPolygon"
        ? geometry.coordinates
        : [];

  polygonGroups.forEach((polygon) => {
    polygon.forEach((ring) => {
      ring.forEach((coordinate) => callback(coordinate));
    });
  });
}

function buildBoundaryProjection(features, coordinateMode) {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  let pointCount = 0;

  features.forEach((feature) => {
    walkGeometryCoordinates(feature.geometry, ([x, y]) => {
      const projected = normaliseBoundaryCoordinate(coordinateMode, x, y);

      if (!Number.isFinite(projected.x) || !Number.isFinite(projected.y)) {
        return;
      }

      minX = Math.min(minX, projected.x);
      maxX = Math.max(maxX, projected.x);
      minY = Math.min(minY, projected.y);
      maxY = Math.max(maxY, projected.y);
      pointCount += 1;
    });
  });

  if (pointCount === 0) {
    return () => ({
      x: RENT_EXPLORER_MAP_VIEWBOX.width / 2,
      y: RENT_EXPLORER_MAP_VIEWBOX.height / 2
    });
  }

  const innerWidth = RENT_EXPLORER_MAP_VIEWBOX.width - RENT_EXPLORER_MAP_VIEWBOX.padding * 2;
  const innerHeight = RENT_EXPLORER_MAP_VIEWBOX.height - RENT_EXPLORER_MAP_VIEWBOX.padding * 2;
  const scale = Math.min(
    innerWidth / (maxX - minX),
    innerHeight / (maxY - minY)
  );
  const offsetX =
    RENT_EXPLORER_MAP_VIEWBOX.padding +
    (innerWidth - (maxX - minX) * scale) / 2 -
    minX * scale;
  const offsetY =
    RENT_EXPLORER_MAP_VIEWBOX.padding +
    (innerHeight - (maxY - minY) * scale) / 2 +
    maxY * scale;

  return (x, y) => {
    const projected = normaliseBoundaryCoordinate(coordinateMode, x, y);
    return {
      x: projected.x * scale + offsetX,
      y: offsetY - projected.y * scale
    };
  };
}

function buildGeometryPath(geometry, projectPoint) {
  if (!geometry) return "";

  const polygonGroups =
    geometry.type === "Polygon"
      ? [geometry.coordinates]
      : geometry.type === "MultiPolygon"
        ? geometry.coordinates
        : [];

  return polygonGroups
    .flatMap((polygon) =>
      polygon.map((ring) =>
        ring
          .filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y))
          .map(([lng, lat], index) => {
            const point = projectPoint(lng, lat);
            const prefix = index === 0 ? "M" : "L";
            return `${prefix} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`;
          })
          .join(" ")
      )
    )
    .filter(Boolean)
    .map((ringPath) => `${ringPath} Z`)
    .join(" ");
}

function buildFeatureLabelPoint(feature, projection, coordinateMode) {
  const props = feature.properties || {};

  if (
    coordinateMode === "projected" &&
    Number.isFinite(Number(props.BNG_E)) &&
    Number.isFinite(Number(props.BNG_N))
  ) {
    return projection(Number(props.BNG_E), Number(props.BNG_N));
  }

  if (Number.isFinite(Number(props.LONG)) && Number.isFinite(Number(props.LAT))) {
    return projection(Number(props.LONG), Number(props.LAT));
  }

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  walkGeometryCoordinates(feature.geometry, ([x, y]) => {
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  });

  if (![minX, maxX, minY, maxY].every(Number.isFinite)) {
    return null;
  }

  return projection((minX + maxX) / 2, (minY + maxY) / 2);
}

function getMapCenterPoint() {
  return {
    x: RENT_EXPLORER_MAP_VIEWBOX.width / 2,
    y: RENT_EXPLORER_MAP_VIEWBOX.height / 2
  };
}

function clampRentExplorerMapPan(panX, panY, zoom = rentExplorerState.mapZoom) {
  if (zoom <= RENT_EXPLORER_MAP_MIN_ZOOM) {
    return { x: 0, y: 0 };
  }

  const horizontalSlack = 28;
  const verticalSlack = 28;
  const maxPanX = ((zoom - 1) * RENT_EXPLORER_MAP_VIEWBOX.width) / 2 + horizontalSlack;
  const maxPanY = ((zoom - 1) * RENT_EXPLORER_MAP_VIEWBOX.height) / 2 + verticalSlack;

  return {
    x: Math.max(-maxPanX, Math.min(maxPanX, panX)),
    y: Math.max(-maxPanY, Math.min(maxPanY, panY))
  };
}

function projectMapPointToViewport(point) {
  if (!point) return null;

  const center = getMapCenterPoint();

  return {
    x: center.x + rentExplorerState.mapPanX + rentExplorerState.mapZoom * (point.x - center.x),
    y: center.y + rentExplorerState.mapPanY + rentExplorerState.mapZoom * (point.y - center.y)
  };
}

function isViewportPointVisible(point, padding = 18) {
  const projected = projectMapPointToViewport(point);

  if (!projected) {
    return false;
  }

  return (
    projected.x >= -padding &&
    projected.x <= RENT_EXPLORER_MAP_VIEWBOX.width + padding &&
    projected.y >= -padding &&
    projected.y <= RENT_EXPLORER_MAP_VIEWBOX.height + padding
  );
}

function getSvgPointFromClient(clientX, clientY) {
  const svg = $("rentMapSvg");
  const rect = svg.getBoundingClientRect();

  if (!rect.width || !rect.height) {
    return getMapCenterPoint();
  }

  return {
    x: ((clientX - rect.left) / rect.width) * RENT_EXPLORER_MAP_VIEWBOX.width,
    y: ((clientY - rect.top) / rect.height) * RENT_EXPLORER_MAP_VIEWBOX.height
  };
}

function updateMapInteractionHint() {
  const hintNode = $("rentMapInteractionHint");
  const zoomPercent = Math.round(rentExplorerState.mapZoom * 100);

  hintNode.textContent =
    rentExplorerState.mapZoom >= RENT_EXPLORER_LABEL_ZOOM_THRESHOLD
      ? `Zoom ${zoomPercent}%: area names are shown for the visible districts. Drag to pan across the map.`
      : `Zoom ${zoomPercent}%: drag to pan and zoom in to ${Math.round(RENT_EXPLORER_LABEL_ZOOM_THRESHOLD * 100)}% to show district names.`;
}

function renderRentExplorerMapLabels() {
  const labelsNode = $("rentMapRegionLabels");
  const items = rentExplorerState.summary?.items || [];
  const features = rentExplorerState.boundaryGeoJson?.features || [];

  if (items.length === 0 || features.length === 0) {
    labelsNode.innerHTML = "";
    return;
  }

  const itemsByCode = new Map(items.map((item) => [item.area_code, item]));
  const selectedCodeSet = new Set(rentExplorerState.selectedAreaCodes);
  const labelFeatures = [];
  const seenCodes = new Set();

  const pushFeature = (feature) => {
    const areaCode = feature?.properties?.LAD24CD;

    if (!areaCode || seenCodes.has(areaCode) || !feature._labelPoint) {
      return;
    }

    if (!isViewportPointVisible(feature._labelPoint)) {
      return;
    }

    seenCodes.add(areaCode);
    labelFeatures.push(feature);
  };

  if (rentExplorerState.mapZoom >= RENT_EXPLORER_LABEL_ZOOM_THRESHOLD) {
    features
      .filter((feature) => itemsByCode.has(feature.properties?.LAD24CD))
      .sort((left, right) => {
        const leftCode = left.properties?.LAD24CD;
        const rightCode = right.properties?.LAD24CD;
        const leftSelectedScore = selectedCodeSet.has(leftCode) ? 0 : 1;
        const rightSelectedScore = selectedCodeSet.has(rightCode) ? 0 : 1;

        if (leftSelectedScore !== rightSelectedScore) {
          return leftSelectedScore - rightSelectedScore;
        }

        return String(left.properties?.LAD24NM || leftCode).localeCompare(
          String(right.properties?.LAD24NM || rightCode)
        );
      })
      .forEach(pushFeature);
  } else {
    const focusFeature = rentExplorerState.boundaryFeaturesByCode.get(rentExplorerState.focusedAreaCode);
    pushFeature(focusFeature);
    rentExplorerState.selectedAreaCodes
      .map((areaCode) => rentExplorerState.boundaryFeaturesByCode.get(areaCode))
      .forEach(pushFeature);
  }

  labelsNode.innerHTML = labelFeatures
    .slice(0, RENT_EXPLORER_LABEL_LIMIT)
    .map((feature) => {
      const areaCode = feature.properties?.LAD24CD;
      const projectedPoint = projectMapPointToViewport(feature._labelPoint);
      const classNames = [
        "map-area-label",
        selectedCodeSet.has(areaCode) ? "is-selected" : "",
        rentExplorerState.focusedAreaCode === areaCode ? "is-focused" : ""
      ]
        .filter(Boolean)
        .join(" ");

      return `
        <text
          class="${classNames}"
          x="${projectedPoint.x.toFixed(2)}"
          y="${projectedPoint.y.toFixed(2)}"
          text-anchor="middle"
        >
          ${escapeHtml(feature.properties?.LAD24NM || areaCode)}
        </text>
      `;
    })
    .join("");
}

function applyRentExplorerMapTransform() {
  const viewportNode = $("rentMapViewport");

  if (!viewportNode) {
    return;
  }

  const clampedPan = clampRentExplorerMapPan(
    rentExplorerState.mapPanX,
    rentExplorerState.mapPanY,
    rentExplorerState.mapZoom
  );

  rentExplorerState.mapPanX = clampedPan.x;
  rentExplorerState.mapPanY = clampedPan.y;

  const center = getMapCenterPoint();

  viewportNode.setAttribute(
    "transform",
    [
      `translate(${(center.x + rentExplorerState.mapPanX).toFixed(2)} ${(center.y + rentExplorerState.mapPanY).toFixed(2)})`,
      `scale(${rentExplorerState.mapZoom.toFixed(3)})`,
      `translate(${-center.x.toFixed(2)} ${-center.y.toFixed(2)})`
    ].join(" ")
  );

  $("rentMapZoomStatus").textContent = `${Math.round(rentExplorerState.mapZoom * 100)}%`;
  updateMapInteractionHint();
  renderRentExplorerMapLabels();
}

function setRentExplorerMapZoom(nextZoom, anchorPoint = getMapCenterPoint()) {
  const clampedZoom = Math.max(
    RENT_EXPLORER_MAP_MIN_ZOOM,
    Math.min(RENT_EXPLORER_MAP_MAX_ZOOM, nextZoom)
  );
  const currentZoom = rentExplorerState.mapZoom;

  if (Math.abs(clampedZoom - currentZoom) < 0.001) {
    return;
  }

  const center = getMapCenterPoint();
  rentExplorerState.mapPanX += (currentZoom - clampedZoom) * (anchorPoint.x - center.x);
  rentExplorerState.mapPanY += (currentZoom - clampedZoom) * (anchorPoint.y - center.y);
  rentExplorerState.mapZoom = clampedZoom;

  if (clampedZoom === RENT_EXPLORER_MAP_MIN_ZOOM) {
    rentExplorerState.mapPanX = 0;
    rentExplorerState.mapPanY = 0;
  }

  applyRentExplorerMapTransform();
}

function resetRentExplorerMapViewport() {
  rentExplorerState.mapZoom = RENT_EXPLORER_MAP_MIN_ZOOM;
  rentExplorerState.mapPanX = 0;
  rentExplorerState.mapPanY = 0;
  applyRentExplorerMapTransform();
}

function initialiseRentExplorerMapInteractions() {
  if (rentExplorerState.mapInteractionsBound) {
    return;
  }

  const svg = $("rentMapSvg");
  const zoomInButton = $("rentMapZoomInBtn");
  const zoomOutButton = $("rentMapZoomOutBtn");
  const resetButton = $("rentMapResetViewBtn");

  zoomInButton.addEventListener("click", () => {
    setRentExplorerMapZoom(rentExplorerState.mapZoom * RENT_EXPLORER_MAP_ZOOM_STEP);
  });

  zoomOutButton.addEventListener("click", () => {
    setRentExplorerMapZoom(rentExplorerState.mapZoom / RENT_EXPLORER_MAP_ZOOM_STEP);
  });

  resetButton.addEventListener("click", () => {
    resetRentExplorerMapViewport();
  });

  svg.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const anchorPoint = getSvgPointFromClient(event.clientX, event.clientY);
      const zoomFactor = event.deltaY < 0 ? RENT_EXPLORER_MAP_ZOOM_STEP : 1 / RENT_EXPLORER_MAP_ZOOM_STEP;
      setRentExplorerMapZoom(rentExplorerState.mapZoom * zoomFactor, anchorPoint);
    },
    { passive: false }
  );

  svg.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) {
      return;
    }

    rentExplorerState.mapDragPointerId = event.pointerId;
    rentExplorerState.mapDragLastClientX = event.clientX;
    rentExplorerState.mapDragLastClientY = event.clientY;
    rentExplorerState.mapDragStartClientX = event.clientX;
    rentExplorerState.mapDragStartClientY = event.clientY;
    rentExplorerState.mapDragMoved = false;
    rentExplorerState.mapDragActive = false;
  });

  svg.addEventListener("pointermove", (event) => {
    if (rentExplorerState.mapDragPointerId !== event.pointerId) {
      return;
    }

    if (
      Math.abs(event.clientX - rentExplorerState.mapDragStartClientX) > RENT_EXPLORER_MAP_DRAG_THRESHOLD ||
      Math.abs(event.clientY - rentExplorerState.mapDragStartClientY) > RENT_EXPLORER_MAP_DRAG_THRESHOLD
    ) {
      rentExplorerState.mapDragMoved = true;
    }

    if (!rentExplorerState.mapDragMoved) {
      return;
    }

    if (!rentExplorerState.mapDragActive) {
      rentExplorerState.mapDragActive = true;
      svg.classList.add("is-dragging");

      if (typeof svg.setPointerCapture === "function") {
        svg.setPointerCapture(event.pointerId);
      }
    }

    const rect = svg.getBoundingClientRect();

    if (!rect.width || !rect.height) {
      return;
    }

    const deltaX =
      ((event.clientX - rentExplorerState.mapDragLastClientX) / rect.width) * RENT_EXPLORER_MAP_VIEWBOX.width;
    const deltaY =
      ((event.clientY - rentExplorerState.mapDragLastClientY) / rect.height) * RENT_EXPLORER_MAP_VIEWBOX.height;

    rentExplorerState.mapPanX += deltaX;
    rentExplorerState.mapPanY += deltaY;
    rentExplorerState.mapDragLastClientX = event.clientX;
    rentExplorerState.mapDragLastClientY = event.clientY;

    applyRentExplorerMapTransform();
  });

  const finishMapDrag = (event) => {
    if (rentExplorerState.mapDragPointerId !== event.pointerId) {
      return;
    }

    if (rentExplorerState.mapDragActive && typeof svg.releasePointerCapture === "function") {
      svg.releasePointerCapture(event.pointerId);
    }

    svg.classList.remove("is-dragging");

    if (rentExplorerState.mapDragActive) {
      rentExplorerState.suppressNextRegionClick = true;
      window.setTimeout(() => {
        rentExplorerState.suppressNextRegionClick = false;
      }, 120);
    }

    rentExplorerState.mapDragPointerId = null;
    rentExplorerState.mapDragActive = false;
    rentExplorerState.mapDragMoved = false;
  };

  svg.addEventListener("pointerup", finishMapDrag);
  svg.addEventListener("pointercancel", finishMapDrag);

  rentExplorerState.mapInteractionsBound = true;
  applyRentExplorerMapTransform();
}

async function ensureBoundaryGeoJsonLoaded() {
  if (rentExplorerState.boundaryGeoJson) {
    return rentExplorerState.boundaryGeoJson;
  }

  if (!rentExplorerState.boundaryLoadPromise) {
    rentExplorerState.boundaryLoadPromise = fetch(getGeoJsonPath(), {
      headers: { "Accept": "application/json" }
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load boundary GeoJSON (HTTP ${response.status}).`);
        }
        return response.json();
      })
      .then((geoJson) => {
        const coordinateMode = detectBoundaryCoordinateMode(geoJson);
        const projection = buildBoundaryProjection(geoJson.features || [], coordinateMode);

        (geoJson.features || []).forEach((feature) => {
          feature._mapPath = buildGeometryPath(feature.geometry, projection);
          feature._labelPoint = buildFeatureLabelPoint(feature, projection, coordinateMode);
        });

        rentExplorerState.boundaryGeoJson = geoJson;
        rentExplorerState.boundaryProjection = projection;
        rentExplorerState.boundaryFeaturesByCode = new Map(
          (geoJson.features || []).map((feature) => [feature.properties?.LAD24CD, feature])
        );

        return geoJson;
      })
      .catch((error) => {
        rentExplorerState.boundaryLoadPromise = null;
        throw error;
      });
  }

  return rentExplorerState.boundaryLoadPromise;
}

function getRentExplorerItem(areaCode) {
  return rentExplorerState.summary?.items?.find((item) => item.area_code === areaCode) || null;
}

function getRentExplorerSelectedItems() {
  return rentExplorerState.selectedAreaCodes
    .map((areaCode) => getRentExplorerItem(areaCode))
    .filter(Boolean);
}

function getRentExplorerSeriesColor(areaCode) {
  const index = rentExplorerState.selectedAreaCodes.indexOf(areaCode);
  return RENT_EXPLORER_SERIES_COLORS[index % RENT_EXPLORER_SERIES_COLORS.length] || "#2563eb";
}

function getRentExplorerColor(metric, value, min, max) {
  const numericValue = Number(value);

  if (metric === "annual_change") {
    const spread = Math.max(Math.abs(min), Math.abs(max), 1);
    const ratio = Math.max(-1, Math.min(1, numericValue / spread));
    const hue = ratio >= 0 ? 165 : 8;
    const saturation = 65 + Math.abs(ratio) * 18;
    const lightness = 78 - Math.abs(ratio) * 28;
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  }

  const safeSpan = max - min || 1;
  const t = Math.max(0, Math.min(1, (numericValue - min) / safeSpan));
  const hue = 210 - t * 58;
  const saturation = 66 + t * 16;
  const lightness = 84 - t * 34;
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

function renderRentExplorerSearchResults() {
  const resultsNode = $("rentExplorerSearchResults");
  const query = $("rentExplorerAreaSearch").value.trim().toLowerCase();
  const items = rentExplorerState.summary?.items || [];

  if (!query) {
    resultsNode.innerHTML = "";
    return;
  }

  const matches = items
    .filter((item) =>
      item.area_name.toLowerCase().includes(query) ||
      item.area_code.toLowerCase().includes(query)
    )
    .slice(0, 8);

  if (matches.length === 0) {
    resultsNode.innerHTML = `<span class="tag-chip">No area matches "${escapeHtml(query)}"</span>`;
    return;
  }

  resultsNode.innerHTML = matches
    .map((item) => `
      <button
        type="button"
        class="explorer-search-chip"
        data-area-code="${escapeHtml(item.area_code)}"
      >
        ${escapeHtml(item.area_name)} (${escapeHtml(item.area_code)})
      </button>
    `)
    .join("");

  resultsNode.querySelectorAll("[data-area-code]").forEach((button) => {
    button.addEventListener("click", async () => {
      await toggleRentExplorerArea(button.dataset.areaCode);
    });
  });
}

function renderRentExplorerLegend() {
  const legendNode = $("rentMapLegend");
  const items = rentExplorerState.summary?.items || [];
  const metric = rentExplorerState.summary?.metric || getRentExplorerMetric();

  if (items.length === 0) {
    legendNode.innerHTML = "";
    return;
  }

  const values = items.map((item) => Number(item.value)).filter(Number.isFinite);
  const min = Math.min(...values);
  const max = Math.max(...values);

  legendNode.innerHTML = `
    <strong>${escapeHtml(getRentExplorerMetricLabel(metric))}</strong>
    <div class="legend-gradient"></div>
    <div class="legend-range">
      <span>${escapeHtml(formatRentExplorerValue(metric, min))}</span>
      <span>${escapeHtml(formatRentExplorerValue(metric, max))}</span>
    </div>
  `;
}

function renderRentExplorerFocus(areaCode) {
  const focusNode = $("rentMapFocus");
  const item = getRentExplorerItem(areaCode);
  const metric = rentExplorerState.summary?.metric || getRentExplorerMetric();

  if (!item) {
    focusNode.innerHTML = `
      <div class="empty-state">Hover over an area or select a district to inspect its latest snapshot value.</div>
    `;
    return;
  }

  focusNode.innerHTML = `
    <div class="map-focus-card">
      <div class="kv-card">
        <div class="kv-key">Area</div>
        <div class="kv-value">${escapeHtml(item.area_name)}</div>
      </div>
      <div class="kv-card">
        <div class="kv-key">Area Code</div>
        <div class="kv-value">${escapeHtml(item.area_code)}</div>
      </div>
      <div class="kv-card">
        <div class="kv-key">${escapeHtml(getRentExplorerMetricLabel(metric))}</div>
        <div class="kv-value">${escapeHtml(formatRentExplorerValue(metric, item.value))}</div>
      </div>
      <div class="kv-card">
        <div class="kv-key">Annual Change</div>
        <div class="kv-value">${escapeHtml(formatRentExplorerValue("annual_change", item.annual_change))}</div>
      </div>
      <div class="kv-card">
        <div class="kv-key">Region</div>
        <div class="kv-value">${escapeHtml(item.region_or_country_name || "Unknown")}</div>
      </div>
      <div class="kv-card">
        <div class="kv-key">Snapshot Month</div>
        <div class="kv-value">${escapeHtml(item.time_period)}</div>
      </div>
    </div>
  `;
}

function renderRentExplorerSelection() {
  const container = $("rentExplorerSelection");
  const meta = $("rentExplorerSelectionMeta");
  const selectedItems = getRentExplorerSelectedItems();

  meta.textContent = `${selectedItems.length} / ${RENT_EXPLORER_MAX_SELECTION} selected`;

  if (selectedItems.length === 0) {
    container.innerHTML = "";
    return;
  }

  container.innerHTML = selectedItems
    .map((item) => `
      <span class="selection-chip" style="--chip-accent: ${getRentExplorerSeriesColor(item.area_code)}">
        ${escapeHtml(item.area_name)}
        <button type="button" aria-label="Remove ${escapeHtml(item.area_name)}" data-remove-area="${escapeHtml(item.area_code)}">x</button>
      </span>
    `)
    .join("");

  container.querySelectorAll("[data-remove-area]").forEach((button) => {
    button.addEventListener("click", async () => {
      await toggleRentExplorerArea(button.dataset.removeArea);
    });
  });
}

function renderRentExplorerMap() {
  const regionsNode = $("rentMapRegions");
  const items = rentExplorerState.summary?.items || [];
  const metric = rentExplorerState.summary?.metric || getRentExplorerMetric();
  const features = rentExplorerState.boundaryGeoJson?.features || [];

  if (items.length === 0 || features.length === 0) {
    regionsNode.innerHTML = "";
    $("rentMapRegionLabels").innerHTML = "";
    renderRentExplorerFocus(null);
    applyRentExplorerMapTransform();
    return;
  }

  const itemsByCode = new Map(items.map((item) => [item.area_code, item]));
  const values = items.map((item) => Number(item.value)).filter(Number.isFinite);
  const min = Math.min(...values);
  const max = Math.max(...values);

  regionsNode.innerHTML = features
    .map((feature) => {
      const areaCode = feature.properties?.LAD24CD;
      const areaName = feature.properties?.LAD24NM || areaCode;
      const item = itemsByCode.get(areaCode);
      const isSelected = rentExplorerState.selectedAreaCodes.includes(areaCode);
      const fill = item ? getRentExplorerColor(metric, item.value, min, max) : "#e5edf7";
      const stroke = isSelected ? getRentExplorerSeriesColor(areaCode) : "#94a3b8";
      const strokeWidth = isSelected ? 2.6 : item ? 0.9 : 0.7;
      const opacity = item ? 0.92 : 0.55;
      const labelText = item
        ? `${areaName}: ${formatRentExplorerValue(metric, item.value)}`
        : `${areaName}: no data for this snapshot`;

      return `
        <path
          class="map-region${item ? " has-data" : " is-empty"}${isSelected ? " is-selected" : ""}"
          data-area-code="${escapeHtml(areaCode)}"
          d="${feature._mapPath || ""}"
          fill="${fill}"
          stroke="${stroke}"
          stroke-width="${strokeWidth}"
          fill-opacity="${opacity}"
          fill-rule="evenodd"
          tabindex="${item ? "0" : "-1"}"
          aria-label="${escapeHtml(labelText)}"
        >
          <title>${escapeHtml(labelText)}</title>
        </path>
      `;
    })
    .join("");

  regionsNode.querySelectorAll(".map-region").forEach((region) => {
    const areaCode = region.dataset.areaCode;
    const item = itemsByCode.get(areaCode);
    const areaName = rentExplorerState.boundaryFeaturesByCode.get(areaCode)?.properties?.LAD24NM || areaCode;

    region.addEventListener("mouseenter", () => {
      if (!item) return;
      rentExplorerState.focusedAreaCode = areaCode;
      renderRentExplorerFocus(areaCode);
      renderRentExplorerMapLabels();
    });

    region.addEventListener("focus", () => {
      if (!item) return;
      rentExplorerState.focusedAreaCode = areaCode;
      renderRentExplorerFocus(areaCode);
      renderRentExplorerMapLabels();
    });

    region.addEventListener("mouseleave", () => {
      const fallbackAreaCode =
        rentExplorerState.selectedAreaCodes[0] ||
        rentExplorerState.summary?.items?.[0]?.area_code ||
        null;
      rentExplorerState.focusedAreaCode = fallbackAreaCode;
      renderRentExplorerFocus(fallbackAreaCode);
      renderRentExplorerMapLabels();
    });

    region.addEventListener("click", async () => {
      if (rentExplorerState.suppressNextRegionClick) {
        return;
      }
      if (!item) {
        setRentExplorerMessage(`${areaName} has no official rent data for the current snapshot.`, "error");
        return;
      }
      await toggleRentExplorerArea(areaCode);
    });

    region.addEventListener("keydown", async (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (rentExplorerState.suppressNextRegionClick) {
          return;
        }
        if (!item) {
          setRentExplorerMessage(`${areaName} has no official rent data for the current snapshot.`, "error");
          return;
        }
        await toggleRentExplorerArea(areaCode);
      }
    });
  });

  applyRentExplorerMapTransform();
}

function extractRentExplorerSeriesValue(point, metric, bedrooms) {
  if (bedrooms === "overall") {
    if (metric === "index_value") return point?.overall?.index;
    return point?.overall?.[metric];
  }

  const bedroomKey =
    bedrooms === "1" ? "one_bed" : bedrooms === "2" ? "two_bed" : "three_bed";
  const bedroomStats = point?.[bedroomKey];

  if (!bedroomStats) return null;
  if (metric === "index_value") return bedroomStats.index;
  if (metric === "rental_price") return bedroomStats.rental_price;
  return null;
}

function renderRentExplorerEmptyChart(message) {
  $("rentTrendModeNote").textContent = "";
  $("rentTrendChart").innerHTML = `
    <div class="trend-empty">
      <div class="empty-state">${escapeHtml(message)}</div>
    </div>
  `;
  $("rentTrendStats").innerHTML = "";
}

function getTrendComparisonMode(seriesCollection) {
  return seriesCollection.length > 1 ? "relative" : "absolute";
}

function buildTrendSeriesForMode(seriesCollection, mode) {
  if (mode === "absolute") {
    return seriesCollection;
  }

  return seriesCollection.map((series) => {
    const baseline = series.points[0]?.value;

    return {
      ...series,
      points: series.points.map((point) => ({
        ...point,
        value: baseline ? ((point.value / baseline) - 1) * 100 : 0
      }))
    };
  });
}

function formatTrendAxisValue(mode, metric, value) {
  if (mode === "relative") {
    const prefix = value > 0 ? "+" : "";
    return `${prefix}${decimalFormatter.format(value)}%`;
  }

  return formatRentExplorerAxisValue(metric, value);
}

function getTrendAxisLabel(mode, metric) {
  if (mode === "relative") {
    return "Change From First Month";
  }

  return getRentExplorerMetricLabel(metric);
}

function isValidYearMonth(value) {
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(value);
}

function getTrendRangeValue(inputId) {
  const value = $(inputId).value.trim();
  return value === "" ? undefined : value;
}

function syncTrendRangeInputs(summary) {
  const fromInput = $("rentExplorerFrom");
  const toInput = $("rentExplorerTo");
  const minTimePeriod = summary?.min_time_period || "";
  const maxTimePeriod = summary?.max_time_period || "";
  const defaultTo = summary?.resolved_time_period || maxTimePeriod || "";
  const currentRangeKey = `${minTimePeriod}|${defaultTo}|${maxTimePeriod}`;
  const rangeChanged = rentExplorerState.lastSummaryRangeKey !== currentRangeKey;

  const currentFrom = fromInput.value.trim();
  const currentTo = toInput.value.trim();

  const shouldResetFrom =
    !currentFrom ||
    !isValidYearMonth(currentFrom) ||
    (minTimePeriod && currentFrom < minTimePeriod) ||
    (maxTimePeriod && currentFrom > maxTimePeriod) ||
    rangeChanged;
  const shouldResetTo =
    !currentTo ||
    !isValidYearMonth(currentTo) ||
    (minTimePeriod && currentTo < minTimePeriod) ||
    (maxTimePeriod && currentTo > maxTimePeriod) ||
    rangeChanged;

  if (shouldResetFrom) {
    fromInput.value = "";
  }

  if (shouldResetTo) {
    toInput.value = "";
  }

  if (fromInput.value && toInput.value && fromInput.value > toInput.value) {
    fromInput.value = "";
    toInput.value = "";
  }

  fromInput.placeholder = minTimePeriod ? `full history from ${minTimePeriod}` : "e.g. 2020-01";
  toInput.placeholder = defaultTo ? `up to ${defaultTo}` : "e.g. 2024-12";

  rentExplorerState.lastSummaryRangeKey = currentRangeKey;
}

function resolveTrendRangeInputs() {
  const from = getTrendRangeValue("rentExplorerFrom");
  const to = getTrendRangeValue("rentExplorerTo");

  if (from && !isValidYearMonth(from)) {
    throw new Error("Trend From must be in YYYY-MM format.");
  }

  if (to && !isValidYearMonth(to)) {
    throw new Error("Trend To must be in YYYY-MM format.");
  }

  if (from && to && from > to) {
    throw new Error("Trend From must be earlier than or equal to Trend To.");
  }

  return { from, to };
}

function extractRentExplorerSeriesPoints(series, metric, bedrooms) {
  return series
    .map((point) => ({
      time_period: point.time_period,
      value: extractRentExplorerSeriesValue(point, metric, bedrooms)
    }))
    .filter((point) => point.value !== null && point.value !== undefined)
    .map((point) => ({
      ...point,
      value: Number(point.value)
    }))
    .filter((point) => Number.isFinite(point.value));
}

function renderRentExplorerTrendChart(seriesCollection, metric, mode) {
  const chartNode = $("rentTrendChart");
  const chartSeries = buildTrendSeriesForMode(seriesCollection, mode);
  const allValues = chartSeries.flatMap((series) => series.points.map((point) => point.value));
  const allPeriods = [...new Set(chartSeries.flatMap((series) => series.points.map((point) => point.time_period)))].sort();

  if (allValues.length === 0 || allPeriods.length === 0) {
    renderRentExplorerEmptyChart("No trend data available for the selected areas and date range.");
    return;
  }

  const width = 820;
  const height = 360;
  const margin = { top: 24, right: 24, bottom: 62, left: 78 };

  let minValue = Math.min(...allValues);
  let maxValue = Math.max(...allValues);

  if (minValue === maxValue) {
    minValue -= 1;
    maxValue += 1;
  }

  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const padding = (maxValue - minValue) * 0.12;
  minValue -= padding;
  maxValue += padding;

  const getX = (timePeriod) => {
    const index = allPeriods.indexOf(timePeriod);
    if (allPeriods.length === 1) {
      return margin.left + innerWidth / 2;
    }
    return margin.left + (index / (allPeriods.length - 1)) * innerWidth;
  };

  const getY = (value) => margin.top + ((maxValue - value) / (maxValue - minValue)) * innerHeight;

  let gridHtml = "";
  const yTickCount = 4;

  for (let tick = 0; tick <= yTickCount; tick += 1) {
    const y = margin.top + (tick / yTickCount) * innerHeight;
    const labelValue = maxValue - (tick / yTickCount) * (maxValue - minValue);
    gridHtml += `
      <line class="trend-grid" x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}"></line>
      <text class="trend-tick-label" x="${margin.left - 12}" y="${y + 4}" text-anchor="end">
        ${escapeHtml(formatTrendAxisValue(mode, metric, labelValue))}
      </text>
    `;
  }

  const xStep = Math.max(1, Math.ceil(allPeriods.length / 6));
  let xTickHtml = "";
  allPeriods.forEach((timePeriod, index) => {
    if (index % xStep !== 0 && index !== allPeriods.length - 1) return;
    const x = getX(timePeriod);
    xTickHtml += `
      <line class="trend-grid" x1="${x}" y1="${margin.top}" x2="${x}" y2="${height - margin.bottom}"></line>
      <text class="trend-tick-label" x="${x}" y="${height - margin.bottom + 24}" text-anchor="middle">
        ${escapeHtml(timePeriod)}
      </text>
    `;
  });

  const seriesHtml = chartSeries
    .map((series, index) => {
      const color = RENT_EXPLORER_SERIES_COLORS[index % RENT_EXPLORER_SERIES_COLORS.length];
      const path = series.points
        .map((point, pointIndex) => `${pointIndex === 0 ? "M" : "L"} ${getX(point.time_period)} ${getY(point.value)}`)
        .join(" ");

      const points = series.points
        .map((point) => `
          <circle
            class="trend-point"
            cx="${getX(point.time_period)}"
            cy="${getY(point.value)}"
            r="5"
            fill="${color}"
          ></circle>
        `)
        .join("");

      return `
        <path class="trend-line" d="${path}" stroke="${color}"></path>
        ${points}
      `;
    })
    .join("");

  chartNode.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Rent trend comparison chart">
      ${gridHtml}
      ${xTickHtml}
      <line class="trend-axis" x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}"></line>
      <line class="trend-axis" x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}"></line>
      ${seriesHtml}
      <text class="trend-axis-label" x="${width / 2}" y="${height - 12}" text-anchor="middle">Time Period</text>
      <text class="trend-axis-label" transform="translate(20 ${height / 2}) rotate(-90)" text-anchor="middle">
        ${escapeHtml(getTrendAxisLabel(mode, metric))}
      </text>
    </svg>
  `;
}

function renderRentExplorerTrendStats(seriesCollection, metric, mode) {
  const statsNode = $("rentTrendStats");

  statsNode.innerHTML = seriesCollection
    .map((series, index) => {
      const color = RENT_EXPLORER_SERIES_COLORS[index % RENT_EXPLORER_SERIES_COLORS.length];
      const firstPoint = series.points[0];
      const lastPoint = series.points[series.points.length - 1];
      const delta = lastPoint.value - firstPoint.value;
      const relativeChange = firstPoint.value ? ((lastPoint.value / firstPoint.value) - 1) * 100 : 0;

      return `
        <div class="trend-stat-card">
          <h4 style="color: ${color}">${escapeHtml(series.item.area_name)}</h4>
          <p><strong>Latest:</strong> ${escapeHtml(formatRentExplorerValue(metric, lastPoint.value))}</p>
          <p><strong>Change:</strong> ${escapeHtml(formatRentExplorerValue(metric, delta))}</p>
          ${mode === "relative" ? `<p><strong>Relative:</strong> ${escapeHtml(formatTrendAxisValue("relative", metric, relativeChange))}</p>` : ""}
          <p><strong>Points:</strong> ${escapeHtml(String(series.points.length))}</p>
          <p><strong>Range:</strong> ${escapeHtml(firstPoint.time_period)} to ${escapeHtml(lastPoint.time_period)}</p>
        </div>
      `;
    })
    .join("");
}

async function loadRentExplorerTrendComparison() {
  const selectedItems = getRentExplorerSelectedItems();

  if (selectedItems.length === 0) {
    renderRentExplorerEmptyChart("Select one or more areas to render their rent trends.");
    return;
  }

  const metric = getRentExplorerMetric();
  const bedrooms = getRentExplorerBedrooms();
  const { from, to } = resolveTrendRangeInputs();

  $("rentTrendChart").innerHTML = `
    <div class="trend-empty">
      <div class="empty-state">Loading trend comparison...</div>
    </div>
  `;
  $("rentTrendStats").innerHTML = "";

  const results = await Promise.allSettled(
    selectedItems.map(async (item) => {
      const qs = buildQuery({ from, to });
      const series = await fetchJsonData(
        `/rent_stats_official/areas/${encodeURIComponent(item.area_code)}/rent-stats${qs}`
      );
      const points = extractRentExplorerSeriesPoints(series, metric, bedrooms);
      return { item, points };
    })
  );

  const successfulSeries = results
    .filter((result) => result.status === "fulfilled" && result.value.points.length > 0)
    .map((result) => result.value);
  const failures = results.filter((result) => result.status === "rejected");
  const comparisonMode = getTrendComparisonMode(successfulSeries);

  if (successfulSeries.length === 0) {
    const fallbackMessage =
      failures[0]?.reason?.message ||
      "No trend data is available for the selected areas and filters.";
    renderRentExplorerEmptyChart(fallbackMessage);
    setRentExplorerMessage(fallbackMessage, "error");
    return;
  }

  $("rentTrendModeNote").textContent =
    comparisonMode === "relative"
      ? `Multiple areas selected: chart is normalised to percentage change from each area's first month so the trend is visible.${from || to ? " Update button applied your date filter." : " No date filter is applied."}`
      : `Single area selected: chart is shown in absolute values.${from || to ? " Update button applied your date filter." : " Showing the full available history."}`;

  renderRentExplorerTrendChart(successfulSeries, metric, comparisonMode);
  renderRentExplorerTrendStats(successfulSeries, metric, comparisonMode);

  if (failures.length > 0) {
    setRentExplorerMessage("Some selected areas could not be loaded for the requested trend range.", "error");
  } else {
    setRentExplorerMessage("Trend comparison updated from the official rent API.", "success");
  }
}

async function toggleRentExplorerArea(areaCode) {
  const existingIndex = rentExplorerState.selectedAreaCodes.indexOf(areaCode);

  if (existingIndex >= 0) {
    rentExplorerState.selectedAreaCodes.splice(existingIndex, 1);
  } else {
    if (rentExplorerState.selectedAreaCodes.length >= RENT_EXPLORER_MAX_SELECTION) {
      setRentExplorerMessage(`You can compare up to ${RENT_EXPLORER_MAX_SELECTION} areas at once.`, "error");
      return;
    }

    rentExplorerState.selectedAreaCodes.push(areaCode);
  }

  rentExplorerState.focusedAreaCode =
    (rentExplorerState.selectedAreaCodes.includes(areaCode) ? areaCode : null) ||
    rentExplorerState.selectedAreaCodes[0] ||
    areaCode ||
    rentExplorerState.summary?.items?.[0]?.area_code ||
    null;

  renderRentExplorerSelection();
  renderRentExplorerMap();
  renderRentExplorerFocus(rentExplorerState.focusedAreaCode);
  await loadRentExplorerTrendComparison();
}

async function loadRentExplorerSummary() {
  syncRentExplorerBedrooms();
  $("rentExplorerSnapshotMeta").textContent = "Loading official rent data...";

  const qs = buildQuery({
    time_period: $("rentExplorerTimePeriod").value.trim(),
    metric: getRentExplorerMetric(),
    bedrooms: getRentExplorerBedrooms()
  });

  try {
    const [summary] = await Promise.all([
      fetchJsonData(`/rent_stats_official/map/summary${qs}`),
      ensureBoundaryGeoJsonLoaded()
    ]);
    rentExplorerState.summary = summary;
    rentExplorerState.selectedAreaCodes = rentExplorerState.selectedAreaCodes.filter((areaCode) =>
      summary.items.some((item) => item.area_code === areaCode)
    );

    syncTrendRangeInputs(summary);

    rentExplorerState.focusedAreaCode =
      rentExplorerState.selectedAreaCodes[0] ||
      summary.items[0]?.area_code ||
      null;

    $("rentExplorerSnapshotMeta").textContent =
      `Snapshot ${summary.resolved_time_period} · ${summary.item_count} area(s) · ${getRentExplorerMetricLabel(summary.metric)}`;

    renderRentExplorerLegend();
    renderRentExplorerSelection();
    renderRentExplorerSearchResults();
    renderRentExplorerMap();
    renderRentExplorerFocus(rentExplorerState.focusedAreaCode);

    if (rentExplorerState.selectedAreaCodes.length > 0) {
      await loadRentExplorerTrendComparison();
    } else {
      renderRentExplorerEmptyChart("Select one or more areas to render their rent trends.");
      setRentExplorerMessage("Map snapshot refreshed from the official rent API.", "success");
    }
  } catch (error) {
    rentExplorerState.summary = null;
    $("rentExplorerSnapshotMeta").textContent = "Unable to load official rent data.";
    $("rentMapLegend").innerHTML = "";
    $("rentMapRegions").innerHTML = "";
    $("rentMapRegionLabels").innerHTML = "";
    renderRentExplorerSearchResults();
    renderRentExplorerFocus(null);
    renderRentExplorerEmptyChart(error.message);
    setRentExplorerMessage(error.message, "error");
  }
}

function resetRentExplorer() {
  $("rentExplorerTimePeriod").value = "";
  $("rentExplorerMetric").value = "rental_price";
  $("rentExplorerBedrooms").value = "overall";
  $("rentExplorerFrom").value = "";
  $("rentExplorerTo").value = "";
  $("rentExplorerAreaSearch").value = "";
  rentExplorerState.selectedAreaCodes = [];
  rentExplorerState.focusedAreaCode = null;
  rentExplorerState.lastSummaryRangeKey = null;
  renderRentExplorerSearchResults();
  syncRentExplorerBedrooms();
  resetRentExplorerMapViewport();
  loadRentExplorerSummary();
}

$("mapSaveConfigBtn").addEventListener("click", async () => {
  saveConfig();
  setRentExplorerMessage("API base URL saved for the standalone map page.", "success");
  await loadRentExplorerSummary();
});

$("rentExplorerLoadBtn").addEventListener("click", async () => {
  await loadRentExplorerSummary();
});

$("rentExplorerApplyTrendBtn").addEventListener("click", async () => {
  if (rentExplorerState.selectedAreaCodes.length === 0) {
    setRentExplorerMessage("Select an area first, then apply an optional trend date filter.", "info");
    return;
  }

  try {
    await loadRentExplorerTrendComparison();
  } catch (error) {
    renderRentExplorerEmptyChart(error.message);
    setRentExplorerMessage(error.message, "error");
  }
});

$("rentExplorerResetBtn").addEventListener("click", () => {
  resetRentExplorer();
});

$("rentExplorerMetric").addEventListener("change", async () => {
  syncRentExplorerBedrooms();
  await loadRentExplorerSummary();
});

$("rentExplorerBedrooms").addEventListener("change", async () => {
  await loadRentExplorerSummary();
});

$("rentExplorerTimePeriod").addEventListener("change", async () => {
  await loadRentExplorerSummary();
});

$("rentExplorerFrom").addEventListener("keydown", async (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    $("rentExplorerApplyTrendBtn").click();
  }
});

$("rentExplorerTo").addEventListener("keydown", async (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    $("rentExplorerApplyTrendBtn").click();
  }
});

$("rentExplorerAreaSearch").addEventListener("input", () => {
  renderRentExplorerSearchResults();
});

loadConfig();
syncRentExplorerBedrooms();
initialiseRentExplorerMapInteractions();
loadRentExplorerSummary();
