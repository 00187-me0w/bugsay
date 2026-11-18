/* Bugsay: availability dashboard. Polls every 30s while the tab is visible. */
(function () {
    "use strict";

    var U = window.Bugsay, esc = U.esc, peso = U.peso;
    var icons = window.BUGSAY.vehicleIcons;
    var form = document.getElementById("dash-form");
    var grid = document.querySelector("[data-grid]");
    var updated = document.querySelector("[data-updated]");
    var REFRESH_MS = 30000;
    var timer = 0, inflight = null;

    function stat(name, html) { document.querySelector('[data-stat="' + name + '"]').innerHTML = html; }

    function row(label, icon, left, capacity, price) {
        return '<div class="dash-row"><span class="name">' + (icon ? '<i class="fa-solid ' + icon + '" aria-hidden="true"></i> ' : "") +
            esc(label) + ' <span class="caption">' + peso(price) + "</span></span>" + U.meter(left, capacity) +
            '<span class="count">' + left + "<small>/" + capacity + "</small></span></div>";
    }

    function card(s) {
        var a = s.availability, st = a.status;
        var link = "/" + (a.seats.length ? "schedules" : "vehicle") + "?" + new URLSearchParams({
            origin: s.origin, destination: s.destination, date: form.elements.date.value
        });
        return '<article class="dash-card' + (st.bookable ? "" : " is-cancelled") + '">' +
            "<header><div><h3>" + esc(s.origin_name) + " → " + esc(s.destination_name) + "</h3><p>" + esc(s.company) +
            (s.vessel ? " · " + esc(s.vessel) : "") + " · " + esc(s.kind) + "</p></div>" +
            '<span class="pill pill--' + esc(st.status) + '">' + esc(st.label) + "</span></header>" +
            '<div class="dash-time">' + esc(s.depart_label) + ' <small>→ ' + esc(s.arrive_label) + (s.next_day ? " (+1)" : "") + "</small></div>" +
            (st.note ? '<p class="footnote" style="color:var(--red)">' + esc(st.note) + "</p>" : "") +
            '<div class="dash-rows"><span class="dash-sub">Seats</span>' +
            a.seats.map(function (x) { return row(x.type, null, x.left, x.capacity, x.price); }).join("") + "</div>" +
            (a.vehicles.length ? '<div class="dash-rows"><span class="dash-sub">Vehicle deck</span>' +
                a.vehicles.map(function (x) { return row(x.type, icons[x.type], x.left, x.capacity, x.price); }).join("") + "</div>" : "") +
            "<footer><span class=\"footnote tabular\">" + a.seats_left + " of " + a.seats_total + " seats left</span>" +
            (st.bookable && a.seats_left ? '<a class="btn btn-secondary" style="min-height:34px" href="' + link + '">Book</a>' : "") +
            "</footer></article>";
    }

    function load() {
        var params = new URLSearchParams(new FormData(form));
        history.replaceState(null, "", "/availability?" + params);
        if (inflight) inflight.abort();
        inflight = new AbortController();
        return fetch("/api/availability?" + params, { signal: inflight.signal })
            .then(function (r) { return r.json(); })
            .then(function (body) {
                var t = body.totals;
                stat("sailings", t.sailings);
                stat("seats", t.seats_left + "<small> / " + t.seats_total + "</small>");
                stat("fill", (t.seats_total ? Math.round((1 - t.seats_left / t.seats_total) * 100) : 0) + "<small>%</small>");
                stat("cancelled", t.cancelled);
                grid.innerHTML = body.sailings.length ? body.sailings.map(card).join("")
                    : '<div class="results-note" style="grid-column:1/-1">No sailings match on ' + esc(U.prettyDate(body.date)) + ".</div>";
                var time = new Date(body.generated_at).toLocaleTimeString("en-PH", { hour: "numeric", minute: "2-digit" });
                updated.textContent = "Live · updated " + time;
            })
            .catch(function (err) {
                if (err.name === "AbortError") return;
                updated.textContent = "Couldn't refresh. Retrying…";
            });
    }

    function schedule() {
        clearTimeout(timer);
        timer = setTimeout(function () {
            if (document.visibilityState === "visible") load().then(schedule); else schedule();
        }, REFRESH_MS);
    }

    form.addEventListener("change", function () { load(); schedule(); });
    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible") { load(); schedule(); }
    });
    load();
    schedule();
})();
