/* Bugsay: shared helpers + behaviour (nav, segmented controls, search form). */
(function () {
    "use strict";

    var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    // ---------------------------------------------------------- helpers
    var U = window.Bugsay = {
        esc: function (value) {
            return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) {
                return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
            });
        },
        peso: function (n) { return "₱" + Math.round(Number(n)).toLocaleString("en-PH"); },
        prettyDate: function (iso) {
            var d = new Date(iso + "T00:00:00");
            return d.toLocaleDateString("en-PH", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
        },
        // Capsule showing how much is left. animate: fill from empty; i: cascade index.
        meter: function (left, capacity, animate, i) {
            var pct = capacity ? left / capacity : 0;
            var cls = pct <= 0.2 ? " critical" : pct <= 0.5 ? " low" : "";
            return '<span class="meter' + cls + (animate ? " animate" : "") + '" style="--pct:' + pct.toFixed(3) +
                (i ? ";--i:" + i : "") + '" role="img" aria-label="' + left + " of " + capacity + ' left"></span>';
        },
        // Tick a number from its current on-screen value to a new one (interruptible).
        countTo: function (el, to, format, dur) {
            format = format || U.peso;
            dur = dur || 380;
            var from = el._value != null ? el._value : (parseInt((el.textContent || "0").replace(/[^\d-]/g, ""), 10) || 0);
            el._value = to;
            if (el._raf) cancelAnimationFrame(el._raf);
            clearTimeout(el._settle);
            if (reduceMotion.matches || from === to || document.visibilityState !== "visible") {
                el.innerHTML = format(to);
                return;
            }
            var start = performance.now();
            // rAF pauses in background tabs; make sure the final value always lands.
            el._settle = setTimeout(function () { cancelAnimationFrame(el._raf); el.innerHTML = format(to); }, dur + 100);
            (function frame(now) {
                var t = Math.min((now - start) / dur, 1);
                var e = 1 - Math.pow(1 - t, 3);
                el.innerHTML = format(Math.round(from + (to - from) * e));
                if (t < 1) el._raf = requestAnimationFrame(frame);
            })(start);
        },
        // Restart a one-shot CSS animation class (e.g. "bump", "shake").
        replay: function (el, cls) {
            if (!el || reduceMotion.matches) return;
            el.classList.remove(cls);
            void el.offsetWidth;
            el.classList.add(cls);
            el.addEventListener("animationend", function () { el.classList.remove(cls); }, { once: true });
        },
        reduceMotion: reduceMotion
    };

    // ------------------------------------------------------- scroll reveal
    // Things further down the page rise in as they scroll into view, cascading
    // within a group. Hidden only when JS runs and motion is allowed.
    var REVEAL = [".section-head", ".features > *", ".advisories > *", ".destinations > *", ".port-list > *",
                  ".faq > *", ".campus > *", ".cta", ".map-card", ".stats > *", ".route-tabs", ".ad-slot",
                  ".ticket-hero", ".checklist", ".summary"];
    if (!reduceMotion.matches && "IntersectionObserver" in window) {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                var el = entry.target;
                el.classList.add("in");
                io.unobserve(el);
                // Hand transforms back to hover effects once the entrance is done.
                setTimeout(function () { el.removeAttribute("data-reveal"); el.classList.remove("in"); }, 1400);
            });
        }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
        document.querySelectorAll(REVEAL.join(",")).forEach(function (el) {
            if (el.closest(".hero, .page-head, .sheet")) return;
            var siblings = el.parentElement ? Array.prototype.indexOf.call(el.parentElement.children, el) : 0;
            el.style.setProperty("--i", Math.min(siblings, 6));
            el.setAttribute("data-reveal", "");
            io.observe(el);
        });
    }

    // --------------------------------------------------------------- nav
    var navbar = document.querySelector(".navbar");
    var toggle = document.querySelector(".nav-toggle");
    var menu = document.getElementById("nav-menu");
    if (toggle && menu) {
        toggle.addEventListener("click", function () {
            var open = menu.classList.toggle("open");
            toggle.setAttribute("aria-expanded", open ? "true" : "false");
            toggle.querySelector("i").className = open ? "fa-solid fa-xmark" : "fa-solid fa-bars";
        });
    }
    // Scroll edge effect: only show the nav's edge once content slides under it.
    if (navbar) {
        var onScroll = function () { navbar.classList.toggle("scrolled", window.scrollY > 4); };
        window.addEventListener("scroll", onScroll, { passive: true });
        onScroll();
    }

    // ---------------------------------------------- segmented controls
    function syncSegment(group) {
        var items = group.querySelectorAll("input, [role=tab]");
        items.forEach(function (el, i) {
            if (el.checked || el.getAttribute("aria-selected") === "true") group.style.setProperty("--index", i);
        });
    }
    document.querySelectorAll("[data-segmented]").forEach(function (group) {
        group.addEventListener("change", function () { syncSegment(group); });
    });

    // Home page route tabs
    var tabGroup = document.querySelector("[data-tabs]");
    if (tabGroup) {
        tabGroup.addEventListener("click", function (e) {
            var tab = e.target.closest("[data-tab]");
            if (!tab) return;
            e.preventDefault();
            var tabs = Array.prototype.slice.call(tabGroup.querySelectorAll("[data-tab]"));
            var from = tabs.findIndex(function (t) { return t.getAttribute("aria-selected") === "true"; });
            var to = tabs.indexOf(tab);
            if (from === to) return;
            tabs.forEach(function (t) {
                var active = t === tab;
                var panel = document.getElementById("panel-" + t.dataset.tab);
                t.setAttribute("aria-selected", active ? "true" : "false");
                if (active) t.setAttribute("aria-current", "page"); else t.removeAttribute("aria-current");
                panel.hidden = !active;
                // Slide in from the side you moved toward, like paging.
                if (active) {
                    panel.removeAttribute("data-enter");
                    void panel.offsetWidth;
                    panel.setAttribute("data-enter", to > from ? "right" : "left");
                }
            });
            syncSegment(tabGroup);
        });
    }

    // ------------------------------------------------------- search form
    var form = document.querySelector("[data-search-form]");
    if (!form) return;

    var routeData = JSON.parse(document.getElementById("route-data").textContent);
    var routes = routeData.routes;
    var ports = routeData.ports;
    var origin = form.elements.origin;
    var dest = form.elements.destination;
    var date = form.elements.date;
    var returnDate = form.elements.return_date;
    var returnField = form.querySelector("[data-return-field]");
    var swapBtn = form.querySelector("[data-swap]");
    var roundNote = form.querySelector("[data-round-note]");

    function hasRoute(from, to) { return (routes[from] || []).indexOf(to) !== -1; }

    function fillDestinations(preferred) {
        var reachable = routes[origin.value] || [];
        dest.innerHTML = "";
        reachable.forEach(function (key) {
            var opt = document.createElement("option");
            opt.value = key;
            opt.textContent = ports[key].name;
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
        if (round && !returnDate.value && date.value) {
            var d = new Date(date.value + "T00:00:00"); d.setDate(d.getDate() + 3);
            var pad = function (n) { return String(n).padStart(2, "0"); };
            returnDate.value = d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
        }
    }

    // Origins that have no sailings in this mode (e.g. vehicles) aren't offered.
    if (!routes[origin.value]) origin.value = Object.keys(routes)[0];
    fillDestinations(dest.dataset.selected || dest.value);
    updateState();

    origin.addEventListener("change", function () { fillDestinations(dest.value); updateState(); });
    dest.addEventListener("change", updateState);
    date.addEventListener("change", updateState);
    form.querySelectorAll("input[name=trip]").forEach(function (r) { r.addEventListener("change", updateState); });

    swapBtn.addEventListener("click", function () {
        var from = origin.value, to = dest.value;
        if (!hasRoute(to, from)) return;
        origin.value = to;
        fillDestinations(from);
        updateState();
        swapBtn.classList.toggle("spin");
    });

    form.addEventListener("submit", function () {
        if (!isRound() || returnField.hidden) returnDate.disabled = true;
        setTimeout(function () { returnDate.disabled = false; }, 0);
    });
})();
