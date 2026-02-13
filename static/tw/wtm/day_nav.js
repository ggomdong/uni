(function () {
    function ymdToCompact(ymd) {
        return (ymd || "").replace(/-/g, "");
    }

    function ymToCompact(ym) {
        return (ym || "").replace(/-/g, "");
    }

    function addDays(ymd, delta) {
        var y = parseInt(ymd.slice(0, 4), 10);
        var m = parseInt(ymd.slice(5, 7), 10) - 1;
        var d = parseInt(ymd.slice(8, 10), 10);
        var dt = new Date(y, m, d);
        dt.setDate(dt.getDate() + delta);
        var yy = String(dt.getFullYear());
        var mm = String(dt.getMonth() + 1).padStart(2, "0");
        var dd = String(dt.getDate()).padStart(2, "0");
        return yy + "-" + mm + "-" + dd;
    }

    function addMonths(ym, delta) {
        var y = parseInt(ym.slice(0, 4), 10);
        var m = parseInt(ym.slice(5, 7), 10) - 1;
        var dt = new Date(y, m, 1);
        dt.setMonth(dt.getMonth() + delta);
        var yy = String(dt.getFullYear());
        var mm = String(dt.getMonth() + 1).padStart(2, "0");
        return yy + "-" + mm;
    }

    function buildUrl(wrap, value) {
        var template = (wrap.dataset.navUrlTemplate || "").trim();
        var compact = wrap.dataset.navMode === "day" ? ymdToCompact(value) : ymToCompact(value);
        return template.split("{value}").join(value).split("{compact}").join(compact);
    }

    function doNavigate(wrap, url) {
        var hxTarget = (wrap.dataset.navHxTarget || "").trim();
        if (hxTarget && window.htmx) {
            var opts = {
                target: hxTarget,
                swap: (wrap.dataset.navHxSwap || "outerHTML").trim() || "outerHTML",
                pushUrl: (wrap.dataset.navHxPushUrl || "true").trim() !== "false"
            };
            var indicator = (wrap.dataset.navHxIndicator || "").trim();
            if (indicator) {
                opts.indicator = indicator;
            }
            window.htmx.ajax("GET", url, opts);
            return;
        }
        window.location.href = url;
    }

    function navigateFromInput(input) {
        var wrap = input.closest("[data-day-nav]");
        if (!wrap || !input.value) {
            return;
        }
        doNavigate(wrap, buildUrl(wrap, input.value));
    }

    function stepFromButton(button) {
        var wrap = button.closest("[data-day-nav]");
        if (!wrap) {
            return;
        }
        var input = wrap.querySelector("[data-day-nav-input]");
        if (!input || !input.value) {
            return;
        }
        var delta = parseInt(button.dataset.dayNavStep || "0", 10);
        var nextValue = wrap.dataset.navMode === "day" ? addDays(input.value, delta) : addMonths(input.value, delta);
        input.value = nextValue;
        doNavigate(wrap, buildUrl(wrap, nextValue));
    }

    document.addEventListener("click", function (event) {
        var btn = event.target.closest("[data-day-nav-step]");
        if (btn) {
            stepFromButton(btn);
        }
    });

    document.addEventListener("change", function (event) {
        if (event.target.matches("[data-day-nav-input]")) {
            navigateFromInput(event.target);
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.target.matches("[data-day-nav-input]")) {
            event.preventDefault();
        }
    });

    document.addEventListener("focusin", function (event) {
        if (event.target.matches("[data-day-nav-input]") && typeof event.target.showPicker === "function") {
            event.target.showPicker();
        }
    });
})();
