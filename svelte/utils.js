const utils = {};

// this element only exists as a separate element on app pages
utils.XSRF = null;
var xsrf_el = document.getElementById('xsrf');
if (xsrf_el) {
	utils.XSRF = xsrf_el.value;
}

utils.joinParams = function(params) {
    var query = [];
    for (var key in params) {
        if (params.hasOwnProperty(key)) {
            var value = params[key];
            if (typeof value === typeof true) {
                // booleans are treated a little bit differently
                value = value ? '1' : '';
            }
            query.push(encodeURIComponent(key) + '=' + encodeURIComponent(value));
        }
    }
    return query.join('&');
};

utils.ajax = function(method, url, data, callback, error_callback) {
    // compatible with IE7+, Firefox, Chrome, Opera, Safari
    var request = new XMLHttpRequest();

    request.onreadystatechange = function() {
        if (request.readyState == 4) {
            if (request.status == 200) {
                var xsrf = request.getResponseHeader('X-Xsrf-Token');
                if (typeof(xsrf) === typeof('') && xsrf.length > 0) {
                    utils.XSRF = xsrf;
                }

                if (callback != null) {
                    if (request.getResponseHeader('Content-Type').indexOf('application/json') === 0) {
                        callback(JSON.parse(request.responseText));
                    }
                    else {
                        callback(request.responseText);
                    }
                }
            }
            else if (error_callback) {
                if (request.getResponseHeader('Content-Type').indexOf('application/json') === 0) {
                    error_callback(request.status, JSON.parse(request.responseText));
                }
                else {
                    error_callback(request.status, request.responseText);
                }
            }
        }
    };

    request.open(method, url);
    if (data != null) {
        if (typeof data === typeof '') {
            // assume JSON if string
            request.setRequestHeader('Content-Type', 'application/json');
            if (utils.XSRF) {
                request.setRequestHeader('X-Xsrf-Token', utils.XSRF);
            }
        }
        else if (data instanceof FormData) {
            if (utils.XSRF) {
                data.append('_xsrf', utils.XSRF);
            }
        }
        else {
            request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');

            if (utils.XSRF) {
                data._xsrf = utils.XSRF;
            }

            data = utils.joinParams(data);
        }

        request.send(data);
    }
    else {
        request.send();
    }
};

utils.toggleForm = function(form, enable) {
    form.disabled = !enable;
    var els = form.querySelectorAll('input,textarea,select');
    for (let i=0; i<els.length; i++) {
        els[i].disabled = !enable;
    }
};

utils.getFormData = function(form) {
    var data = {};
    var form_data = new window.FormData(form);
    // note that for whatever reason "for var in form_data doesn't seem to work
    form_data.forEach(function(value, key) {
        data[key] = value;
    });
    return data;
};

utils.submitForm = function(form, callback) {
    // handles some basic form submission boilerplate
    if (form.disabled) {
        // prevent multiple submits
        return;
    }

    // assemble the all the data from the form into an object
    var form_data = new FormData(form);

    utils.toggleForm(form, false);

    utils.ajax(form.method, form.action, form_data, function(data) {
        // need to set this here in case the callback navigates away from the page and the form no longer exists
        utils.toggleForm(form, true);

		if (callback) {
			callback(data);
		}
    }, function() {
        // this is a failure case where the request didn't work
        utils.toggleForm(form, true);
    });
};

const dt_options = {year: 'numeric', month: 'long', day: 'numeric', hour: 'numeric', minute: 'numeric'};

utils.formatDateTime = function(s) {
	// Python 3 isoformat includes +, but that makes it invalid for JS, so remove it
    //var iso = s.split('+')[0] + 'Z'; // the Z indicates UTC
	var d  = new Date(s);
	return d.toLocaleString('en-US', dt_options);
};

export default utils;
