/* Bugsay: <dialog> sheet with Apple-style motion.
 *
 * - Desktop: centred card that materialises (scale + fade).
 * - Phones: bottom sheet. Drag the grabber/header down to dismiss:
 *   tracks the finger 1:1 from where it was grabbed, rubber-bands upward,
 *   hands the release velocity to a spring, and projects momentum to decide
 *   whether to close. Grabbing it mid-animation picks up from the live
 *   on-screen position (interruptible).
 * - Respects prefers-reduced-motion (cross-fade only).
 */
(function () {
    "use strict";

    var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    var phone = window.matchMedia("(max-width: 640px)");

    // Apple's momentum projection (Designing Fluid Interfaces, WWDC 2018).
    function project(velocity, decelerationRate) {
        decelerationRate = decelerationRate || 0.998;
        return (velocity / 1000) * decelerationRate / (1 - decelerationRate);
    }

    function rubberband(overshoot, dimension) {
        var c = 0.55;
        return (overshoot * dimension * c) / (dimension + c * Math.abs(overshoot));
    }

    // Damped spring described by response (s) and damping ratio, like SwiftUI.
    function spring(opts) {
        var k = Math.pow(2 * Math.PI / (opts.response || 0.35), 2);
        var c = 4 * Math.PI * (opts.damping == null ? 1 : opts.damping) / (opts.response || 0.35);
        var x = opts.from, v = opts.velocity || 0, to = opts.to;
        var last = performance.now(), raf = 0, stopped = false;
        function frame(now) {
            if (stopped) return;
            var dt = Math.min((now - last) / 1000, 1 / 30);
            last = now;
            for (var i = 0; i < 4; i++) {          // sub-steps keep stiff springs stable
                var h = dt / 4;
                var a = -k * (x - to) - c * v;
                v += a * h;
                x += v * h;
            }
            if (Math.abs(x - to) < 0.5 && Math.abs(v) < 20) {
                opts.onUpdate(to);
                if (opts.onDone) opts.onDone();
                return;
            }
            opts.onUpdate(x);
            raf = requestAnimationFrame(frame);
        }
        raf = requestAnimationFrame(frame);
        return {
            stop: function () { stopped = true; cancelAnimationFrame(raf); return { value: x, velocity: v }; }
        };
    }

    function Sheet(dialog) {
        this.dialog = dialog;
        this.y = 0;          // presentation value (px dragged down)
        this.anim = null;
        this.onClose = null;
        var self = this;

        dialog.addEventListener("cancel", function (e) { e.preventDefault(); self.close(); });
        // Tap outside closes, but only when the press also started outside
        // (a drag that ends past the sheet's edge must not count as a tap).
        var downOnBackdrop = false;
        dialog.addEventListener("pointerdown", function (e) { downOnBackdrop = e.target === dialog; });
        dialog.addEventListener("click", function (e) {
            if (e.target === dialog && downOnBackdrop) self.close();
            downOnBackdrop = false;
        });
        dialog.querySelectorAll("[data-close]").forEach(function (b) {
            b.addEventListener("click", function () { self.close(); });
        });

        dialog.querySelectorAll("[data-grabber], [data-drag-handle]").forEach(function (handle) {
            handle.addEventListener("pointerdown", function (e) { self._down(e); });
        });
    }

    Sheet.prototype._set = function (y) {
        this.y = y;
        this.dialog.style.transform = y ? "translateY(" + y + "px)" : "";
    };

    Sheet.prototype.open = function () {
        if (this.anim) { this.anim.stop(); this.anim = null; }
        this._set(0);
        this.dialog.classList.remove("closing");
        this.dialog.showModal();
    };

    Sheet.prototype.close = function (velocity) {
        var self = this, d = this.dialog;
        if (!d.open || d.classList.contains("closing")) return;
        var done = false;
        function finish() {
            if (done) return;
            done = true;
            if (self.anim) { self.anim.stop(); self.anim = null; }
            d.classList.remove("closing", "dragging");
            d.close();
            self._set(0);
            if (self.onClose) self.onClose();
        }
        if (reduceMotion.matches) { d.classList.add("closing"); setTimeout(finish, 200); return; }
        if (phone.matches && (this.y || velocity)) {
            // Continue the drag: spring off-screen at the finger's velocity.
            d.classList.add("dragging");
            if (this.anim) this.anim.stop();
            this.anim = spring({
                from: this.y, to: d.offsetHeight + 40, velocity: Math.max(velocity || 0, 600),
                response: 0.3, damping: 1, onUpdate: function (y) { self._set(y); }, onDone: finish
            });
            return;
        }
        d.classList.add("closing");
        d.addEventListener("animationend", finish, { once: true });
        setTimeout(finish, 400); // animationend can be skipped (background tab, display change)
    };

    Sheet.prototype._down = function (e) {
        if (!phone.matches || e.button > 0 || e.target.closest("button, a, input, select, textarea")) return;
        var self = this, d = this.dialog, handle = e.currentTarget;
        // Interruptible: start from the live on-screen position.
        if (this.anim) { this.anim.stop(); this.anim = null; }
        var startPointer = e.clientY, startY = this.y, height = d.offsetHeight;
        var history = [{ y: e.clientY, t: e.timeStamp }];
        var dragging = false;
        try { handle.setPointerCapture(e.pointerId); } catch (err) { /* pointer already gone */ }

        function move(ev) {
            var delta = ev.clientY - startPointer;
            if (!dragging && Math.abs(delta) < 6) return; // small hysteresis
            dragging = true;
            d.classList.add("dragging");
            var y = startY + delta;
            self._set(y < 0 ? rubberband(y, height) : y);
            history.push({ y: ev.clientY, t: ev.timeStamp });
            if (history.length > 6) history.shift();
        }
        function up(ev) {
            handle.removeEventListener("pointermove", move);
            handle.removeEventListener("pointerup", up);
            handle.removeEventListener("pointercancel", up);
            if (!dragging) { d.classList.remove("dragging"); return; }
            var first = history[0], last = history[history.length - 1];
            var dt = Math.max(last.t - first.t, 1);
            var velocity = (last.y - first.y) / dt * 1000; // px/s
            var projected = self.y + project(velocity);
            if (projected > height * 0.45 || velocity > 1100) {
                self.close(velocity);
            } else {
                // Snap back; slight bounce only because a gesture preceded it.
                self.anim = spring({
                    from: self.y, to: 0, velocity: velocity, response: 0.32, damping: 0.82,
                    onUpdate: function (y) { self._set(y); },
                    onDone: function () { self.anim = null; d.classList.remove("dragging"); }
                });
            }
        }
        handle.addEventListener("pointermove", move);
        handle.addEventListener("pointerup", up);
        handle.addEventListener("pointercancel", up);
    };

    window.BugsaySheet = Sheet;
})();
