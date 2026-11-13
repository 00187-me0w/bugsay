/* Bugsay: schedule search results and the "save trip" dialog. */
(function () {
    "use strict";

    var form = document.getElementById("search-form");
    var results = document.getElementById("results");
    var dialog = document.getElementById("reserve-dialog");
    var reserveForm = document.getElementById("reserve-form");
    var discountRate = (window.BUGSAY && window.BUGSAY.discountRate) || 0.2;
    var tripsById = {};
    var current = null; // { trip, date }

    function esc(value) {
        return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) {
            return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
        });
    }

    function peso(n) { return "₱" + Number(n).toLocaleString("en-PH"); }

    function fareTotal(price, passengers, discounted) {
        var cut = Math.round(price * (1 - discountRate));
        return price * (passengers - discounted) + cut * discounted;
    }

    function prettyDate(iso) {
        var d = new Date(iso + "T00:00:00");
        return d.toLocaleDateString("en-PH", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
    }

    function values() {
        var trip = form.querySelector("input[name=trip]:checked");
        return {
            origin: form.elements.origin.value,
            destination: form.elements.destination.value,
            date: form.elements.date.value,
            returnDate: form.elements.return_date.value,
            round: trip && trip.value === "round",
            passengers: parseInt(form.elements.passengers.value, 10) || 1
        };
    }

    function fetchLeg(origin, destination, date) {
        var url = "/api/trips?" + new URLSearchParams({ origin: origin, destination: destination, date: date });
        return fetch(url).then(function (r) {
            return r.json().then(function (body) {
                if (!r.ok) throw new Error(body.error || "Search failed.");
                return body;
            });
        });
    }

    function card(trip, date, passengers) {
        tripsById[trip.id] = trip;
        var fares = trip.fares.map(function (f) { return esc(f.type) + " " + peso(f.price); }).join(" · ");
        return '' +
            '<div class="schedule-card">' +
            '  <div class="carrier-info">' +
            '    <i class="fa-solid fa-ship carrier-icon" aria-hidden="true"></i>' +
            '    <div><h5>' + esc(trip.company) + '</h5><p>' + esc(trip.kind) +
                     (trip.vessel ? " · " + esc(trip.vessel) : "") + " · " + esc(trip.days_label) + '</p></div>' +
            '  </div>' +
            '  <div class="trip-timeline">' +
            '    <div class="time"><h4>' + esc(trip.depart_label) + '</h4><p>' + esc(trip.origin_name) + '</p></div>' +
            '    <div class="duration">' + esc(trip.duration_label) + '<br><i class="fa-solid fa-ship" aria-hidden="true"></i><br>Direct crossing</div>' +
            '    <div class="time"><h4>' + esc(trip.arrive_label) + (trip.next_day ? ' <sup class="next-day" title="Arrives the next day">+1</sup>' : "") +
                     '</h4><p>' + esc(trip.destination_name) + '</p></div>' +
            '  </div>' +
            '  <div class="trip-price"><span>From, per person</span><h4>' + peso(trip.min_fare) + '</h4>' +
                 (passengers > 1 ? '<span>' + peso(trip.min_fare * passengers) + ' for ' + passengers + '</span>' : "") + '</div>' +
            '  <div class="trip-action"><button type="button" class="btn-primary" data-reserve="' + esc(trip.id) +
                 '" data-date="' + esc(date) + '">Select</button></div>' +
            '  <p class="fare-list">' + fares + '</p>' +
            '</div>';
    }

    function legHtml(title, body, passengers) {
        var html = '<h3 class="results-title">' + esc(title) + ' <span>' + esc(prettyDate(body.date)) + '</span></h3>';
        html += '<div class="schedule-container">';
        if (body.trips.length) {
            html += body.trips.map(function (t) { return card(t, body.date, passengers); }).join("");
        } else if (body.other_days.length) {
            html += '<p class="results-none">No sailings on this day. This route runs on other days:</p><ul class="other-days">' +
                body.other_days.map(function (t) {
                    return '<li><strong>' + esc(t.company) + '</strong> ' + esc(t.depart_label) + ' · ' + esc(t.days_label) + '</li>';
                }).join("") + '</ul>';
        } else {
            html += '<p class="results-none">No sailings listed for this route.</p>';
        }
        html += '<p class="hint"><i class="fa-solid fa-circle-info" aria-hidden="true"></i> Reference schedules—confirm times and fares with the carrier.</p>';
        return html + '</div>';
    }

    function search(pushUrl) {
        var v = values();
        if (!v.origin || !v.destination || !v.date) return;
        if (v.round && v.returnDate && v.returnDate < v.date) {
            results.innerHTML = '<p class="form-error">Your return date is before your departure date.</p>';
            return;
        }

        var params = { origin: v.origin, destination: v.destination, date: v.date, passengers: v.passengers };
        if (v.round) { params.trip = "round"; if (v.returnDate) params.return_date = v.returnDate; }
        if (pushUrl) history.replaceState(null, "", "/schedules?" + new URLSearchParams(params));

        results.innerHTML = '<p class="results-loading"><i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i> Searching sailings…</p>';
        var legs = [fetchLeg(v.origin, v.destination, v.date)];
        var wantReturn = v.round && v.returnDate && form.elements.return_date.required;
        if (wantReturn) legs.push(fetchLeg(v.destination, v.origin, v.returnDate));

        Promise.all(legs).then(function (bodies) {
            tripsById = {};
            var html = legHtml("Departing", bodies[0], v.passengers);
            if (bodies[1]) html += legHtml("Returning", bodies[1], v.passengers);
            results.innerHTML = html;
        }).catch(function (err) {
            results.innerHTML = '<p class="form-error">' + esc(err.message) + '</p>';
        });
    }

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        search(true);
    });

    // ---- Save-trip dialog
    var fareSelect = reserveForm.elements.fare_class;
    var paxSelect = reserveForm.elements.passengers;
    var discSelect = reserveForm.elements.discounted;
    var totalEl = dialog.querySelector("[data-total]");
    var errorEl = dialog.querySelector("[data-form-error]");

    function fillDiscounted() {
        var pax = parseInt(paxSelect.value, 10);
        var keep = Math.min(parseInt(discSelect.value, 10) || 0, pax);
        discSelect.innerHTML = "";
        for (var i = 0; i <= pax; i++) {
            var o = document.createElement("option");
            o.value = i; o.textContent = i;
            discSelect.appendChild(o);
        }
        discSelect.value = keep;
    }

    function updateTotal() {
        if (!current) return;
        var fare = current.trip.fares.filter(function (f) { return f.type === fareSelect.value; })[0];
        if (!fare) return;
        totalEl.textContent = peso(fareTotal(fare.price, parseInt(paxSelect.value, 10), parseInt(discSelect.value, 10)));
    }

    results.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-reserve]");
        if (!btn) return;
        var trip = tripsById[btn.dataset.reserve];
        current = { trip: trip, date: btn.dataset.date };

        dialog.querySelector("[data-reserve-summary]").innerHTML =
            '<strong>' + esc(trip.origin_name) + ' → ' + esc(trip.destination_name) + '</strong><br>' +
            esc(trip.company) + ' · ' + esc(prettyDate(current.date)) + ' · departs ' + esc(trip.depart_label);

        fareSelect.innerHTML = trip.fares.map(function (f) {
            return '<option value="' + esc(f.type) + '">' + esc(f.type) + ' — ' + peso(f.price) + '</option>';
        }).join("");
        paxSelect.value = String(values().passengers);
        fillDiscounted();
        errorEl.hidden = true;
        updateTotal();
        dialog.showModal();
    });

    fareSelect.addEventListener("change", updateTotal);
    paxSelect.addEventListener("change", function () { fillDiscounted(); updateTotal(); });
    discSelect.addEventListener("change", updateTotal);

    reserveForm.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!reserveForm.reportValidity()) return;
        var submit = reserveForm.querySelector("button[type=submit]");
        var label = submit.innerHTML;
        submit.disabled = true;
        submit.innerHTML = '<i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i> Saving…';
        errorEl.hidden = true;

        fetch("/api/bookings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                trip_id: current.trip.id,
                date: current.date,
                fare_class: fareSelect.value,
                passengers: parseInt(paxSelect.value, 10),
                discounted: parseInt(discSelect.value, 10),
                name: reserveForm.elements.name.value,
                email: reserveForm.elements.email.value
            })
        }).then(function (r) {
            return r.json().then(function (body) { return { ok: r.ok, body: body }; });
        }).then(function (res) {
            if (res.ok) { window.location.href = res.body.url; return; }
            var errs = res.body.errors || { form: "Something went wrong." };
            errorEl.textContent = Object.keys(errs).map(function (k) { return errs[k]; }).join(" ");
            errorEl.hidden = false;
        }).catch(function () {
            errorEl.textContent = "Couldn't reach Bugsay. Check your connection and try again.";
            errorEl.hidden = false;
        }).then(function () {
            submit.disabled = false;
            submit.innerHTML = label;
        });
    });

    // Run a search straight away when the page was opened with a route in the URL.
    var params = new URLSearchParams(window.location.search);
    if (params.get("origin") && params.get("destination")) search(false);
})();
