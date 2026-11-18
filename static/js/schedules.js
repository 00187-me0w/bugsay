/* Bugsay: schedule results with live availability, and the booking sheet
 * (several passenger tickets + vehicles in one transaction). */
(function () {
    "use strict";

    var cfg = window.BUGSAY;
    var U = window.Bugsay;
    var form = document.getElementById("search-form");
    var results = document.getElementById("results");
    var dialog = document.getElementById("book-sheet");
    var bookForm = document.getElementById("book-form");
    var sheet = new window.BugsaySheet(dialog);
    var vehicleMode = cfg.mode === "vehicle";
    var tripsByKey = {};
    var state = null;

    var esc = U.esc, peso = U.peso;

    function discounted(price) { return Math.round(price * (1 - cfg.discountRate)); }

    function searchValues() {
        var el = form.elements;
        var trip = form.querySelector("input[name=trip]:checked");
        return {
            origin: el.origin.value,
            destination: el.destination.value,
            date: el.date.value,
            returnDate: el.return_date.value,
            round: trip && trip.value === "round",
            passengers: el.passengers ? parseInt(el.passengers.value, 10) || 1 : 0,
            vehicleType: el.vehicle_type ? el.vehicle_type.value : ""
        };
    }

    // ------------------------------------------------------------ results

    function fetchLeg(origin, destination, date) {
        var params = { origin: origin, destination: destination, date: date };
        if (vehicleMode) params.mode = "vehicle";
        return fetch("/api/trips?" + new URLSearchParams(params)).then(function (r) {
            return r.json().then(function (body) {
                if (!r.ok) throw new Error(body.error || "Search failed.");
                return body;
            });
        });
    }

    function plainChip(x) { return '<span class="chip">' + esc(x.type) + " " + peso(x.price) + "</span>"; }

    function seatChip(s, i) {
        return '<span class="chip' + (s.left ? "" : " chip--sold") + '">' + esc(s.type) + " " + peso(s.price) +
            ' · <b>' + (s.left ? s.left + " left" : "Sold out") + "</b>" + U.meter(s.left, s.capacity, true, i) + "</span>";
    }

    function vehicleChip(v, i) {
        return '<span class="chip' + (v.left ? "" : " chip--sold") + '"><i class="fa-solid ' + (cfg.vehicleIcons[v.type] || "fa-car") +
            '" aria-hidden="true"></i> ' + esc(v.type) + " " + peso(v.price) + ' · <b>' + (v.left ? v.left + " slots" : "Full") +
            "</b>" + U.meter(v.left, v.capacity, true, i) + "</span>";
    }

    function card(trip, date, wanted, i) {
        var key = trip.id + "|" + date;
        tripsByKey[key] = { trip: trip, date: date };
        var a = trip.availability;
        var status = a.status;
        var price, priceLabel, canBook, foot;

        if (vehicleMode) {
            var vs = a.vehicles.filter(function (v) { return !wanted.vehicleType || v.type === wanted.vehicleType; });
            var open = vs.filter(function (v) { return v.left > 0; });
            price = Math.min.apply(null, (open.length ? open : vs).map(function (v) { return v.price; }));
            priceLabel = wanted.vehicleType ? wanted.vehicleType + " rate" : "Vehicles from";
            canBook = status.bookable && open.length > 0;
            foot = a.vehicles.map(function (x) { return vehicleChip(x, i); }).join("");
        } else {
            var openSeats = a.seats.filter(function (s) { return s.left >= wanted.passengers; });
            price = (openSeats[0] || a.seats[0]).price;
            priceLabel = wanted.passengers > 1 ? "From, per person" : "From";
            canBook = status.bookable && openSeats.length > 0;
            foot = a.seats.map(function (x) { return seatChip(x, i); }).join("");
            if (trip.carries_vehicles) foot += '<span class="chip"><i class="fa-solid fa-car-side" aria-hidden="true"></i> Takes vehicles</span>';
        }
        if (!status.bookable) foot = (vehicleMode ? a.vehicles : a.seats).map(plainChip).join("");
        var btnLabel = !status.bookable ? "Cancelled" : canBook ? "Select" : !vehicleMode ? "Sold out"
            : (wanted.vehicleType && !a.vehicles.some(function (x) { return x.type === wanted.vehicleType; })) ? "No " + wanted.vehicleType : "Full";

        return '' +
            '<article class="trip-card' + (status.bookable ? "" : " is-cancelled") + '" style="--i:' + i + '">' +
            '  <div class="carrier">' +
            '    <span class="carrier-icon"><i class="fa-solid ' + (trip.kind === "Fast craft" ? "fa-bolt" : "fa-ship") + '" aria-hidden="true"></i></span>' +
            '    <div><h3>' + esc(trip.company) + '</h3><p>' + esc(trip.kind) + (trip.vessel ? " · " + esc(trip.vessel) : "") +
                   " · " + esc(trip.days_label) + '</p>' +
            '    <span class="pill pill--' + esc(status.status) + '">' + esc(status.label) + "</span>" +
                   (a.demo ? ' <span class="pill pill--demo" title="Demo inventory until the carrier provides real capacity">Demo seats</span>' : "") +
            '    </div>' +
            '  </div>' +
            '  <div class="timeline">' +
            '    <div class="time"><strong>' + esc(trip.depart_label) + '</strong><span>' + esc(trip.origin_name) + '</span></div>' +
            '    <div class="leg"><span>' + esc(trip.duration_label) + '</span></div>' +
            '    <div class="time"><strong>' + esc(trip.arrive_label) + (trip.next_day ? '<sup class="next-day" title="Arrives the next day">+1</sup>' : "") +
                   '</strong><span>' + esc(trip.destination_name) + '</span></div>' +
            '  </div>' +
            '  <div class="price"><span>' + esc(priceLabel) + '</span><strong>' + (isFinite(price) ? peso(price) : "—") + '</strong></div>' +
            '  <button type="button" class="btn ' + (canBook ? "btn-primary" : "btn-secondary") + '" data-book="' + esc(key) + '"' +
                 (canBook ? "" : " disabled") + '>' + btnLabel + '</button>' +
                 (status.note ? '<p class="status-note"><i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i> ' + esc(status.note) + "</p>" : "") +
            '  <div class="trip-foot">' + foot + '</div>' +
            '</article>';
    }

    function legHtml(title, body, wanted) {
        var html = '<div class="results-title"><h2>' + esc(title) + '</h2><span>' + esc(U.prettyDate(body.date)) + "</span></div>";
        if (body.trips.length) {
            html += '<div class="card-list">' + body.trips.map(function (t, i) { return card(t, body.date, wanted, i); }).join("") + "</div>";
        } else if (body.other_days.length) {
            html += '<div class="results-note">No ' + (vehicleMode ? "vehicle-carrying " : "") + "sailings on this day. This route runs on other days:" +
                '<ul class="other-days">' + body.other_days.map(function (t) {
                    return "<li><strong>" + esc(t.company) + "</strong> " + esc(t.depart_label) + " · " + esc(t.days_label) + "</li>";
                }).join("") + "</ul></div>";
        } else {
            html += '<div class="results-note">No ' + (vehicleMode ? "vehicle-carrying " : "") + "sailings listed for this route.</div>";
        }
        return html;
    }

    function search(updateUrl) {
        var v = searchValues();
        if (!v.origin || !v.destination || !v.date) return;
        if (v.round && v.returnDate && v.returnDate < v.date) {
            results.innerHTML = '<p class="form-error">Your return date is before your departure date.</p>';
            return;
        }
        var params = { origin: v.origin, destination: v.destination, date: v.date };
        if (vehicleMode) { if (v.vehicleType) params.vehicle_type = v.vehicleType; }
        else params.passengers = v.passengers;
        if (v.round) { params.trip = "round"; if (v.returnDate) params.return_date = v.returnDate; }
        if (updateUrl) history.replaceState(null, "", location.pathname + "?" + new URLSearchParams(params));

        results.innerHTML = '<div class="card-list"><div class="skeleton"></div><div class="skeleton"></div></div>';
        var legs = [fetchLeg(v.origin, v.destination, v.date)];
        if (v.round && v.returnDate && form.elements.return_date.required) legs.push(fetchLeg(v.destination, v.origin, v.returnDate));

        return Promise.all(legs).then(function (bodies) {
            tripsByKey = {};
            var html = legHtml("Departing", bodies[0], v);
            if (bodies[1]) html += legHtml("Returning", bodies[1], v);
            html += '<p class="hint"><i class="fa-solid fa-circle-info" aria-hidden="true"></i> Reference schedules and demo seat counts. Confirm times and fares with the carrier.</p>';
            results.innerHTML = html;
        }).catch(function (err) {
            results.innerHTML = '<p class="form-error">' + esc(err.message) + "</p>";
        });
    }

    form.addEventListener("submit", function (e) { e.preventDefault(); search(true); });

    // -------------------------------------------------------- booking sheet

    var accGroup = dialog.querySelector("[data-acc-group]");
    var accList = dialog.querySelector("[data-acc-list]");
    var paxList = dialog.querySelector("[data-pax-list]");
    var vehGroup = dialog.querySelector("[data-veh-group]");
    var vehList = dialog.querySelector("[data-veh-list]");
    var addPax = dialog.querySelector("[data-add-pax]");
    var addVeh = dialog.querySelector("[data-add-veh]");
    var summary = dialog.querySelector("[data-summary]");
    var totalEl = dialog.querySelector("[data-total]");
    var errorEl = dialog.querySelector("[data-form-error]");
    var submitBtn = dialog.querySelector("[data-submit]");

    function seatsFor(type) {
        return state.avail.seats.filter(function (s) { return s.type === type; })[0];
    }
    function vehicleFor(type) {
        return state.avail.vehicles.filter(function (v) { return v.type === type; })[0];
    }
    function vehiclesLeft(type) {
        var v = vehicleFor(type);
        var used = state.vehicles.filter(function (x) { return x.type === type; }).length;
        return v ? v.left - used : 0;
    }

    function renderAcc() {
        accGroup.hidden = state.passengers.length === 0;
        accList.innerHTML = state.avail.seats.map(function (s, i) {
            var enough = s.left >= Math.max(state.passengers.length, 1);
            return '<label class="row choice' + (enough ? "" : " disabled") + '">' +
                '<input type="radio" name="fare_class" value="' + esc(s.type) + '"' + (s.type === state.fareClass ? " checked" : "") +
                (enough ? "" : " disabled") + '>' +
                '<span class="choice-main"><b>' + esc(s.type) + '</b><span class="caption">' +
                (s.left ? s.left + " of " + s.capacity + " seats left" : "Sold out") + "</span>" + U.meter(s.left, s.capacity) + "</span>" +
                '<span class="choice-price">' + peso(s.price) + '</span><span class="check" aria-hidden="true"></span></label>';
        }).join("");
        var sel = seatsFor(state.fareClass);
        dialog.querySelector("[data-acc-note]").textContent = sel ? sel.left + " left in " + sel.type : "";
    }

    function renderPax() {
        paxList.innerHTML = state.passengers.map(function (p, i) {
            var opts = Object.keys(cfg.passengerTypes).map(function (k) {
                return '<option value="' + k + '"' + (k === p.type ? " selected" : "") + ">" + esc(cfg.passengerTypes[k].label) + "</option>";
            }).join("");
            return '<div class="row" data-pax="' + i + '">' +
                '<i class="lead fa-solid fa-user" aria-hidden="true"></i>' +
                '<input type="text" data-field="name" value="' + esc(p.name) + '" placeholder="Passenger ' + (i + 1) + ' full name" autocomplete="' + (i === 0 ? "name" : "off") + '" maxlength="100" aria-label="Passenger ' + (i + 1) + ' full name">' +
                '<select data-field="type" aria-label="Passenger ' + (i + 1) + ' type">' + opts + "</select>" +
                '<button type="button" class="remove" data-remove-pax="' + i + '" aria-label="Remove passenger ' + (i + 1) + '"><i class="fa-solid fa-minus" aria-hidden="true"></i></button>' +
                "</div>";
        }).join("");
        var sel = seatsFor(state.fareClass);
        var cap = Math.min(cfg.maxPassengers, sel ? sel.left : cfg.maxPassengers);
        addPax.disabled = state.passengers.length >= cap;
        dialog.querySelector("[data-pax-note]").textContent = state.passengers.length + " ticket" + (state.passengers.length === 1 ? "" : "s");
    }

    function renderVeh() {
        vehGroup.hidden = state.avail.vehicles.length === 0;
        vehList.innerHTML = state.vehicles.map(function (v, i) {
            var opts = state.avail.vehicles.map(function (o) {
                var left = vehiclesLeft(o.type) + (o.type === v.type ? 1 : 0);
                return '<option value="' + esc(o.type) + '"' + (o.type === v.type ? " selected" : "") + (left > 0 ? "" : " disabled") + ">" +
                    esc(o.type) + " · " + peso(o.price) + "</option>";
            }).join("");
            return '<div class="row row-stack" data-veh="' + i + '">' +
                '<div class="row-line"><i class="lead fa-solid ' + (cfg.vehicleIcons[v.type] || "fa-car") + '" aria-hidden="true" style="background:var(--teal)"></i>' +
                '<input type="text" data-field="plate" value="' + esc(v.plate) + '" placeholder="Plate number" maxlength="12" autocapitalize="characters" aria-label="Vehicle ' + (i + 1) + ' plate number" style="text-transform:uppercase">' +
                '<select data-field="type" aria-label="Vehicle ' + (i + 1) + ' type">' + opts + "</select>" +
                '<button type="button" class="remove" data-remove-veh="' + i + '" aria-label="Remove vehicle ' + (i + 1) + '"><i class="fa-solid fa-minus" aria-hidden="true"></i></button></div>' +
                '<div class="row-line"><input type="text" class="cargo" data-field="cargo" value="' + esc(v.cargo) + '" maxlength="120" placeholder="Cargo (optional), e.g. 20 sacks of rice" aria-label="Vehicle ' + (i + 1) + ' cargo"></div>' +
                "</div>";
        }).join("");
        var anyLeft = state.avail.vehicles.some(function (o) { return vehiclesLeft(o.type) > 0; });
        addVeh.disabled = state.vehicles.length >= cfg.maxVehicles || !anyLeft;
        dialog.querySelector("[data-veh-note]").textContent = state.vehicles.length ? state.vehicles.length + " vehicle" + (state.vehicles.length === 1 ? "" : "s") : "";
    }

    function quote() {
        var fare = seatsFor(state.fareClass);
        var lines = [], total = 0;
        if (state.passengers.length && fare) {
            var n = state.passengers.length;
            var disc = state.passengers.filter(function (p) { return cfg.passengerTypes[p.type].discounted; }).length;
            lines.push([n + " × " + fare.type + " fare", fare.price * n]);
            total += fare.price * n;
            if (disc) {
                var d = (fare.price - discounted(fare.price)) * disc;
                lines.push(["Discount (" + disc + " student/senior/PWD)", -d, "discount"]);
                total -= d;
            }
        }
        var byType = {};
        state.vehicles.forEach(function (v) { byType[v.type] = (byType[v.type] || 0) + 1; });
        Object.keys(byType).forEach(function (t) {
            var price = vehicleFor(t).price;
            lines.push([byType[t] + " × " + t, price * byType[t]]);
            total += price * byType[t];
        });
        var fee = state.passengers.length * cfg.feeTicket + state.vehicles.length * cfg.feeVehicle;
        if (fee) { lines.push(["Bugsay service fee", fee, "muted"]); total += fee; }
        return { lines: lines, total: total };
    }

    function renderSummary() {
        var q = quote();
        summary.innerHTML = q.lines.length ? q.lines.map(function (l) {
            return '<div class="line ' + (l[2] || "") + '"><span>' + esc(l[0]) + "</span><span>" + (l[1] < 0 ? "−" + peso(-l[1]) : peso(l[1])) + "</span></div>";
        }).join("") : '<div class="line muted"><span>Add a passenger or vehicle</span><span></span></div>';
        if (totalEl._value != null && totalEl._value !== q.total && dialog.open) U.replay(totalEl, "bump");
        U.countTo(totalEl, q.total);
        var count = state.passengers.length + state.vehicles.length;
        submitBtn.disabled = count === 0;
        submitBtn.textContent = count ? "Confirm " + count + " ticket" + (count === 1 ? "" : "s") : "Confirm booking";
    }

    function renderAll() { renderAcc(); renderPax(); renderVeh(); renderSummary(); }

    function openSheet(key) {
        var entry = tripsByKey[key];
        var trip = entry.trip, avail = trip.availability;
        var v = searchValues();
        var firstSeat = avail.seats.filter(function (s) { return s.left > 0; })[0];
        var paxCount = vehicleMode ? 0 : Math.min(v.passengers, firstSeat ? firstSeat.left : 0);
        var pickSeat = avail.seats.filter(function (s) { return s.left >= Math.max(paxCount, 1); })[0] || firstSeat;
        state = {
            trip: trip, date: entry.date, avail: avail,
            fareClass: pickSeat ? pickSeat.type : null,
            passengers: [], vehicles: []
        };
        for (var i = 0; i < paxCount; i++) state.passengers.push({ name: "", type: "regular" });
        if (vehicleMode) {
            var vt = avail.vehicles.filter(function (o) { return o.left > 0 && (!v.vehicleType || o.type === v.vehicleType); })[0] ||
                     avail.vehicles.filter(function (o) { return o.left > 0; })[0];
            if (vt) state.vehicles.push({ type: vt.type, plate: "", cargo: "" });
        }
        dialog.querySelector("[data-sheet-sub]").textContent = trip.company + " · " + trip.origin_name + " → " + trip.destination_name +
            " · " + U.prettyDate(entry.date) + ", " + trip.depart_label;
        errorEl.hidden = true;
        totalEl._value = null;
        renderAll();
        sheet.open();
        var firstInput = dialog.querySelector("[data-pax] input, [data-veh] input");
        if (firstInput && window.matchMedia("(min-width: 641px)").matches) firstInput.focus();
    }

    results.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-book]");
        if (btn && !btn.disabled) openSheet(btn.dataset.book);
    });

    // Keep state in sync while typing without re-rendering (keeps focus).
    bookForm.addEventListener("input", function (e) {
        var row = e.target.closest("[data-pax], [data-veh]");
        if (!row) return;
        row.classList.remove("invalid");
        var list = row.dataset.pax != null ? state.passengers : state.vehicles;
        var item = list[parseInt(row.dataset.pax != null ? row.dataset.pax : row.dataset.veh, 10)];
        item[e.target.dataset.field] = e.target.value;
        if (e.target.tagName === "SELECT") {
            if (row.dataset.veh != null) renderVeh();
            renderSummary();
        }
    });

    bookForm.addEventListener("change", function (e) {
        if (e.target.name === "fare_class") {
            state.fareClass = e.target.value;
            renderAcc(); renderPax(); renderSummary();
        }
    });

    addPax.addEventListener("click", function () {
        state.passengers.push({ name: "", type: "regular" });
        if (!state.fareClass || seatsFor(state.fareClass).left < state.passengers.length) {
            var s = state.avail.seats.filter(function (x) { return x.left >= state.passengers.length; })[0];
            if (s) state.fareClass = s.type;
        }
        renderAll();
        paxList.lastElementChild.classList.add("entering");
        var inputs = paxList.querySelectorAll("input");
        inputs[inputs.length - 1].focus({ preventScroll: true });
        paxList.lastElementChild.scrollIntoView({ block: "nearest", behavior: U.reduceMotion.matches ? "auto" : "smooth" });
    });

    addVeh.addEventListener("click", function () {
        var t = state.avail.vehicles.filter(function (o) { return vehiclesLeft(o.type) > 0; })[0];
        if (!t) return;
        state.vehicles.push({ type: t.type, plate: "", cargo: "" });
        renderVeh(); renderSummary();
        vehList.lastElementChild.classList.add("entering");
        var rows = vehList.querySelectorAll("[data-field=plate]");
        rows[rows.length - 1].focus({ preventScroll: true });
        vehList.lastElementChild.scrollIntoView({ block: "nearest", behavior: U.reduceMotion.matches ? "auto" : "smooth" });
    });

    // Removing a row: let it slide out first, then update the list.
    function removeRow(row, done) {
        if (U.reduceMotion.matches || row.classList.contains("leaving")) { done(); return; }
        row.classList.add("leaving");
        setTimeout(done, 170);
    }

    dialog.addEventListener("click", function (e) {
        var rp = e.target.closest("[data-remove-pax]");
        var rv = e.target.closest("[data-remove-veh]");
        if (rp) removeRow(rp.closest(".row"), function () {
            state.passengers.splice(parseInt(rp.dataset.removePax, 10), 1); renderAll();
        });
        if (rv) removeRow(rv.closest(".row"), function () {
            state.vehicles.splice(parseInt(rv.dataset.removeVeh, 10), 1); renderVeh(); renderSummary();
        });
    });

    function showErrors(errors) {
        var messages = [];
        Object.keys(errors).forEach(function (k) {
            var m = k.match(/^(passengers|vehicles)\.(\d+)\./);
            if (m) {
                var row = dialog.querySelector(m[1] === "passengers" ? '[data-pax="' + m[2] + '"]' : '[data-veh="' + m[2] + '"]');
                if (row) row.classList.add("invalid");
            }
            if (messages.indexOf(errors[k]) === -1) messages.push(errors[k]);
        });
        errorEl.textContent = messages.join(" ");
        errorEl.hidden = false;
        // A short shake says "not quite" without a modal alert.
        dialog.querySelectorAll(".row.invalid").forEach(function (r) { U.replay(r, "shake"); });
        U.replay(errorEl, "shake");
        var bad = dialog.querySelector(".invalid input") || errorEl;
        bad.scrollIntoView({ block: "center", behavior: "smooth" });
        if (bad.focus) bad.focus({ preventScroll: true });
    }

    bookForm.addEventListener("submit", function (e) {
        e.preventDefault();
        errorEl.hidden = true;
        var email = bookForm.elements.email;
        if (!email.checkValidity() || !email.value) { showErrors({ email: "Enter a valid email address." }); email.focus(); return; }

        var label = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i> Booking…';
        fetch("/api/bookings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                trip_id: state.trip.id,
                date: state.date,
                fare_class: state.fareClass,
                passengers: state.passengers,
                vehicles: state.vehicles,
                email: email.value,
                payment_method: bookForm.querySelector("input[name=payment_method]:checked").value
            })
        }).then(function (r) {
            return r.json().then(function (body) { return { ok: r.ok, status: r.status, body: body }; });
        }).then(function (res) {
            if (res.ok) { window.location.href = res.body.url; return; }
            if (res.body.availability) {           // someone else took the seats: refresh counts
                state.avail = res.body.availability;
                state.trip.availability = res.body.availability;
                renderAll();
                search(false);
            }
            showErrors(res.body.errors || { form: "Something went wrong. Please try again." });
            submitBtn.disabled = false;
            submitBtn.textContent = label;
        }).catch(function () {
            showErrors({ form: "Couldn't reach Bugsay. Check your connection and try again." });
            submitBtn.disabled = false;
            submitBtn.textContent = label;
        });
    });

    var params = new URLSearchParams(window.location.search);
    if (params.get("origin") && params.get("destination")) search(false);
})();
