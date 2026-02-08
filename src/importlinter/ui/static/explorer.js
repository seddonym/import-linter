let svg = null;
let viewBox = { x: 0, y: 0, width: 0, height: 0 };
let originalViewBox = null;
let isPanning = false;
let startPoint = { x: 0, y: 0 };
let scale = 1;

// Navigation state
let currentModule = null;
let navigationHistory = [];
let vizInstance = null;
let currentPackages = [];

// Settings state
let showImportTotals = false;
let showCycleBreakers = false;

// Client-side cache for rendered graphs
const graphCache = new Map();

async function initViz() {
    vizInstance = await Viz.instance();
}

function buildApiUrl(moduleName) {
    let url = `/api/graph/${encodeURIComponent(moduleName)}`;
    const params = [];
    if (showImportTotals) {
        params.push('show_import_totals=true');
    }
    if (showCycleBreakers) {
        params.push('show_cycle_breakers=true');
    }
    if (params.length) {
        url += '?' + params.join('&');
    }
    return url;
}

function buildCacheKey(moduleName) {
    return `${moduleName}|${showImportTotals}|${showCycleBreakers}`;
}

function onSettingsChange() {
    showImportTotals = document.getElementById('toggle-import-totals').checked;
    showCycleBreakers = document.getElementById('toggle-cycle-breakers').checked;
    loadGraph(currentModule, false);
}

async function loadGraph(moduleName = null, updateHistory = true) {
    const loading = document.getElementById('loading');
    const errorMsg = document.getElementById('error-message');

    // Check cache first
    if (moduleName) {
        const cacheKey = buildCacheKey(moduleName);
        if (graphCache.has(cacheKey)) {
            const cached = graphCache.get(cacheKey);
            restoreFromCache(cached, updateHistory);
            return;
        }
    }

    loading.style.display = 'flex';
    errorMsg.style.display = 'none';

    try {
        const url = buildApiUrl(moduleName);
        const response = await fetch(url);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        currentModule = data.module;
        currentPackages = data.child_packages || [];
        updateBreadcrumb();

        if (updateHistory) {
            updateUrl(currentModule);
        }

        // Modify DOT to add trailing slash to package labels
        let dot = data.dot_string;
        const nodeMatches = dot.matchAll(/^(\s*)"([^"]+)"\n/gm);
        for (const match of nodeMatches) {
            const whitespace = match[1];
            const nodeName = match[2];
            if (currentPackages.includes(nodeName)) {
                dot = dot.replace(`${whitespace}"${nodeName}"\n`, `${whitespace}"${nodeName}" [label="${nodeName}/"]\n`);
            }
        }

        // Render DOT to SVG using viz.js
        if (!vizInstance) {
            await initViz();
        }
        const svgElement = vizInstance.renderSVGElement(dot);

        // Insert SVG into container
        const container = document.getElementById('graph-svg');
        container.innerHTML = '';
        container.appendChild(svgElement);

        svg = container.querySelector('svg');
        loading.style.display = 'none';

        // Setup viewBox for pan/zoom
        const bbox = svg.getBBox();
        const padding = 20;
        viewBox = {
            x: bbox.x - padding,
            y: bbox.y - padding,
            width: bbox.width + padding * 2,
            height: bbox.height + padding * 2
        };
        originalViewBox = { ...viewBox };
        updateViewBox();

        // Setup event handlers
        setupPanZoom();
        setupNodeClicks();

        // Cache the rendered graph
        const cacheKey = buildCacheKey(currentModule);
        graphCache.set(cacheKey, {
            module: currentModule,
            packages: currentPackages,
            svgElement: svgElement.cloneNode(true),
            viewBox: { ...originalViewBox }
        });

    } catch (error) {
        loading.style.display = 'none';
        errorMsg.textContent = `Failed to load graph: ${error.message}`;
        errorMsg.style.display = 'block';
    }
}

function restoreFromCache(cached, updateHistory) {
    currentModule = cached.module;
    currentPackages = [...cached.packages];
    updateBreadcrumb();

    if (updateHistory) {
        updateUrl(currentModule);
    }

    const container = document.getElementById('graph-svg');
    container.innerHTML = '';
    container.appendChild(cached.svgElement.cloneNode(true));

    svg = container.querySelector('svg');

    viewBox = { ...cached.viewBox };
    originalViewBox = { ...cached.viewBox };
    updateViewBox();

    setupPanZoom();
    setupNodeClicks();
}

function updateBreadcrumb() {
    const breadcrumb = document.getElementById('breadcrumb');
    const parts = currentModule.split('.');
    let html = '<span class="prefix">Import graph for</span>';

    for (let i = 0; i < parts.length; i++) {
        const fullPath = parts.slice(0, i + 1).join('.');
        if (i < parts.length - 1) {
            html += `<span class="crumb" onclick="navigateTo('${fullPath}')">${parts[i]}</span>`;
            html += '<span class="separator">/</span>';
        } else {
            html += `<span class="current">${parts[i]}</span>`;
        }
    }

    breadcrumb.innerHTML = html;

    const navSection = document.getElementById('nav-section');
    navSection.style.display = parts.length <= 1 ? 'none' : 'flex';
}

function goUp() {
    const parts = currentModule.split('.');
    if (parts.length <= 1) return;

    const parentModule = parts.slice(0, -1).join('.');
    navigationHistory.push(currentModule);
    loadGraph(parentModule);
}

function navigateTo(moduleName) {
    if (moduleName === currentModule) return;
    navigationHistory.push(currentModule);
    loadGraph(moduleName);
}

function drillDown(relativeNodeName) {
    const childName = relativeNodeName.startsWith('.') ? relativeNodeName.slice(1) : relativeNodeName;
    const fullModuleName = `${currentModule}.${childName}`;
    navigationHistory.push(currentModule);
    loadGraph(fullModuleName);
}

function updateViewBox() {
    if (svg) {
        svg.setAttribute('viewBox', `${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`);
    }
}

function setupPanZoom() {
    const container = document.getElementById('graph-container');

    // Remove existing listeners by cloning
    const newContainer = container.cloneNode(true);
    container.parentNode.replaceChild(newContainer, container);

    // Re-get references after clone
    svg = document.querySelector('#graph-svg svg');

    const graphContainer = document.getElementById('graph-container');

    graphContainer.addEventListener('mousedown', (e) => {
        if (e.button === 0 && e.target.closest('#graph-svg')) {
            isPanning = true;
            startPoint = { x: e.clientX, y: e.clientY };
            graphContainer.style.cursor = 'grabbing';
        }
    });

    graphContainer.addEventListener('mousemove', (e) => {
        if (!isPanning) return;

        const dx = (e.clientX - startPoint.x) * (viewBox.width / graphContainer.clientWidth);
        const dy = (e.clientY - startPoint.y) * (viewBox.height / graphContainer.clientHeight);

        viewBox.x -= dx;
        viewBox.y -= dy;

        startPoint = { x: e.clientX, y: e.clientY };
        updateViewBox();
    });

    graphContainer.addEventListener('mouseup', () => {
        isPanning = false;
        graphContainer.style.cursor = 'grab';
    });

    graphContainer.addEventListener('mouseleave', () => {
        isPanning = false;
        graphContainer.style.cursor = 'grab';
    });

    graphContainer.addEventListener('wheel', (e) => {
        if (!e.target.closest('#graph-svg')) return;
        e.preventDefault();

        const zoomFactor = e.deltaY > 0 ? 1.1 : 0.9;
        zoom(zoomFactor, e.clientX, e.clientY);
    }, { passive: false });
}

function zoom(factor, clientX, clientY) {
    const container = document.getElementById('graph-container');
    const rect = container.getBoundingClientRect();

    const mouseX = viewBox.x + (clientX - rect.left) / rect.width * viewBox.width;
    const mouseY = viewBox.y + (clientY - rect.top) / rect.height * viewBox.height;

    const newWidth = viewBox.width * factor;
    const newHeight = viewBox.height * factor;

    viewBox.x = mouseX - (mouseX - viewBox.x) * factor;
    viewBox.y = mouseY - (mouseY - viewBox.y) * factor;
    viewBox.width = newWidth;
    viewBox.height = newHeight;

    scale /= factor;
    updateViewBox();
}

function zoomIn() {
    const container = document.getElementById('graph-container');
    const rect = container.getBoundingClientRect();
    zoom(0.8, rect.left + rect.width / 2, rect.top + rect.height / 2);
}

function zoomOut() {
    const container = document.getElementById('graph-container');
    const rect = container.getBoundingClientRect();
    zoom(1.25, rect.left + rect.width / 2, rect.top + rect.height / 2);
}

function resetView() {
    if (originalViewBox) {
        viewBox = { ...originalViewBox };
        scale = 1;
        updateViewBox();
    }
}

function setupNodeClicks() {
    if (!svg) return;

    const tooltip = document.getElementById('tooltip');
    const nodes = svg.querySelectorAll('.node');

    nodes.forEach(node => {
        const title = node.querySelector('title');
        const nodeName = title ? title.textContent : 'Unknown';
        const isPackage = currentPackages.includes(nodeName);

        if (isPackage) {
            node.classList.add('package');

            node.addEventListener('click', (e) => {
                e.stopPropagation();
                e.stopImmediatePropagation();
                e.preventDefault();
                if (node.dataset.clicking) return;
                node.dataset.clicking = 'true';
                setTimeout(() => delete node.dataset.clicking, 500);
                tooltip.style.display = 'none';
                drillDown(nodeName);
            });

            node.addEventListener('mouseenter', (e) => {
                const childName = nodeName.startsWith('.') ? nodeName.slice(1) : nodeName;
                tooltip.textContent = `Explore ${currentModule}.${childName}`;
                tooltip.style.display = 'block';
            });

            node.addEventListener('mousemove', (e) => {
                tooltip.style.left = (e.clientX + 10) + 'px';
                tooltip.style.top = (e.clientY + 10) + 'px';
            });

            node.addEventListener('mouseleave', () => {
                tooltip.style.display = 'none';
            });
        }
    });
}

function updateUrl(moduleName) {
    const url = new URL(window.location);
    if (moduleName) {
        url.searchParams.set('module', moduleName);
    } else {
        url.searchParams.delete('module');
    }
    history.pushState({ module: moduleName }, '', url);
}

function getModuleFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('module');
}

// Handle browser back/forward
window.addEventListener('popstate', (event) => {
    const module = event.state?.module || getModuleFromUrl();
    loadGraph(module, false);
});

// Load graph on page load
initViz().then(() => {
    const moduleFromUrl = getModuleFromUrl();
    const initialModule = moduleFromUrl || document.querySelector('#breadcrumb .current')?.textContent;
    loadGraph(initialModule, false);
    history.replaceState({ module: initialModule }, '');
});
