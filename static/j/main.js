var trestle = trestle || {};

trestle.joinParams = function(params) {
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

trestle.ajax = function(method, url, data, callback) {
    // compatible with IE7+, Firefox, Chrome, Opera, Safari
    var request = new XMLHttpRequest();

    request.onreadystatechange = function() {
        if (request.readyState == 4) {
            if (request.status == 200) {
                var xsrf = request.getResponseHeader('X-Xsrf-Token');
                if (typeof(xsrf) === typeof('') && xsrf.length > 0) {
                    trestle.XSRF = xsrf;
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
            if (trestle.XSRF) {
                request.setRequestHeader('X-Xsrftoken', trestle.XSRF);
            }
        }
        else if (data instanceof FormData) {
            if (trestle.XSRF) {
                data.append('_xsrf', trestle.XSRF);
            }
        }
        else {
            request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');

            if (trestle.XSRF) {
                data._xsrf = trestle.XSRF;
            }

            data = trestle.joinParams(data);
        }

        request.send(data);
    }
    else {
        request.send();
    }
};

// this should come as early as possible
window.onerror = function(error, script, line, char) {
    var error_data = {'error': error, 'script': script, 'location': line + ':' + char};
    trestle.ajax('POST', '/logerror', {'javascript': JSON.stringify(error_data)});
};

trestle.logout = function(e) {
    e.preventDefault();
    document.getElementById("logout-form").submit();
};

trestle.logout_link = document.getElementById("logout-link");
if (trestle.logout_link) {
    trestle.logout_link.addEventListener('click', trestle.logout);
}

trestle.upload = function(e) {
    // at the time of submit swaps out a regular url for a blobstore one, then re-submits
    var form = this;
    if (form.getAttribute("data-ready")) {
        return;
    }

    e.preventDefault();
    var inputs = form.getElementsByTagName('input');
    for (var i=0; i < inputs.length; i++) {
        var input = inputs[i];
        if (input.type == 'submit') {
            if (input.disabled) {
                return;
            }
            else {
                input.disabled = true;
                break;
            }
        }
    }

    var data = {'url': form.action, 'csrf': form.csrf.value};
    trestle.ajax('POST', '/api/upload', data, function(response) {
        var response_json = JSON.parse(response);
        form.action = response_json.url;
        form.setAttribute("data-ready", true);
        form.submit();
    });
};

trestle.upload_forms = document.getElementsByClassName("upload-form");
for (var i=0; i < trestle.upload_forms.length; i++) {
    trestle.upload_forms[i].addEventListener('submit', trestle.upload);
}

trestle.MONTHS = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];

trestle.convert_timestamp = function(el) {
    // Python 3 isoformat includes +, but that makes it invalid for JS, so remove it
    var dt_string = el.getAttribute("datetime");
    var iso = dt_string.split('+')[0] + "Z"; // the Z indicates UTC
    var local = new Date(iso);
    var month = trestle.MONTHS[local.getMonth()];
    var date_string = month + " " + local.getDate().toString() + ", " + local.getFullYear().toString();

    var hours = local.getHours();
    var ampm = "AM";
    if (hours > 11) {ampm = "PM";}
    if (hours > 12) {hours -= 12;}
    if (hours === 0) {hours = 12;}

    var minutes = local.getMinutes().toString();
    if (minutes.length < 2) {minutes = "0" + minutes;}

    var time_string = hours.toString() + ":" + minutes + " " + ampm;

    el.innerHTML = date_string + " " + time_string;
};

trestle.times = document.getElementsByTagName("time");
for (var i=0; i < trestle.times.length; i++) {
    trestle.convert_timestamp(trestle.times[i]);
}
