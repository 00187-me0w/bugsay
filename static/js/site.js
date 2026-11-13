/* Bugsay: shared behaviour (nav menu, search form, home tabs). */
(function () {
    "use strict";

    // ---- Mobile nav toggle
    var toggle = document.querySelector(".nav-toggle");
    var menu = document.getElementById("nav-menu");
    if (toggle && menu) {
        toggle.addEventListener("click", function () {
            var open = menu.classList.toggle("open");
            toggle.setAttribute("aria-expanded", open ? "true" : "false");
        });
    }

    // ---- Home page route tabs
    var tabs = document.querySelectorAll("[data-tab]");
    tabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
            tabs.forEach(function (t) {
                var active = t === tab;
                t.classList.toggle("active", active);
                t.setAttribute("aria-selected", active ? "true" : "false");
                var panel = document.getElementById("panel-" + t.dataset.tab);
                if (panel) panel.hidden = !active;
            });
        });
    });

    // ---- Search form
    var form = document.querySelector("[data-search-form]");
    if (!form) return;

    var routeData = JSON.parse(document.getElementById("route-data").textContent);
    var routes = routeData.routes;
    var ports = routeData.ports;
    var origin = form.querySelector("#origin");
    var dest = form.querySelector("#destination");
    var date = form.querySelector("#date");
    var returnDate = form.querySelector("#return_date");
    var returnField = form.querySelector("[data-return-field]");
    var swapBtn = form.querySelector("[data-swap]");
    var roundNote = form.querySelector("[data-round-note]");
    var tripRadios = form.querySelectorAll("input[name=trip]");

    function hasRoute(from, to) {
        return (routes[from] || []).indexOf(to) !== -1;
    }

    function fillDestinations(preferred) {
        var reachable = routes[origin.value] || [];
        dest.innerHTML = "";
        reachable.forEach(function (key) {
            var opt = document.createElement("option");
            opt.value = key;
            opt.textContent = "◎ " + ports[key].name;
            dest.appendChild(opt);
        });
        if (preferred && reachable.indexOf(preferred) !== -1) dest.value = preferred;
    }

    function isRound() {
        var checked = form.querySelector("input[name=trip]:checked");
        return checked && checked.value === "round";
    }

    function updateState() {
        var canReturn = hasRoute(dest.value, origin.value);
        swapBtn.disabled = !canReturn;
        swapBtn.title = canReturn ? "Swap origin and destination"
            : "No sailings listed from " + ports[dest.value].name + " to " + ports[origin.value].name;

        var round = isRound();
        returnField.hidden = !round;
        returnDate.required = round && canReturn;
        roundNote.hidden = !(round && !canReturn);
        roundNote.textContent = round && !canReturn ? "No return sailings listed for this route." : "";

        returnDate.min = date.value || returnDate.min;
        if (round && returnDate.value && returnDate.value < date.value) returnDate.value = date.value;
    }

    fillDestinations(dest.dataset.selected || dest.value);
    updateState();

    origin.addEventListener("change", function () { fillDestinations(dest.value); updateState(); });
    dest.addEventListener("change", updateState);
    date.addEventListener("change", updateState);
    tripRadios.forEach(function (r) { r.addEventListener("change", updateState); });

    swapBtn.addEventListener("click", function () {
        var from = origin.value, to = dest.value;
        if (!hasRoute(to, from)) return;
        origin.value = to;
        fillDestinations(from);
        updateState();
    });

    // Strip empty optional fields so URLs stay tidy.
    form.addEventListener("submit", function () {
        if (!isRound() || returnField.hidden) returnDate.disabled = true;
        setTimeout(function () { returnDate.disabled = false; }, 0);
    });
})();
