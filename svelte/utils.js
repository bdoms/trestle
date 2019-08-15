const utils = {};

// this element only exists as a separate element on app pages
utils.XSRF = null;
var xsrf_el = document.getElementById('xsrf');
if (xsrf_el) {
	utils.XSRF = xsrf_el.value;
}

utils.ajax = function(method, url, data, callback) {
	// compatible with IE7+, Firefox, Chrome, Opera, Safari
	var request = new XMLHttpRequest();

	request.onreadystatechange = function() {
		if (request.readyState == 4 && request.status == 200) {
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
	};

	request.open(method, url, true);
	if (data != null) {
		if (typeof data === typeof '') {
            // assume JSON if string
			request.setRequestHeader('Content-Type', 'application/json');
			if (utils.XSRF) {
				request.setRequestHeader('X-Xsrf-Token', utils.XSRF);
			}
		}
		else {
			request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');

			if (utils.XSRF) {
				data._xsrf = utils.XSRF;
			}

			var query = [];
			for (var key in data) {
				if (data.hasOwnProperty(key)) {
					query.push(encodeURIComponent(key) + '=' + encodeURIComponent(data[key]));
				}
			}
			data = query.join('&');
		}
		request.send(data);
	}
	else {
		request.send();
	}
};

const dt_options = {year: 'numeric', month: 'long', day: 'numeric', hour: 'numeric', minute: 'numeric'};

utils.formatDateTime = function(s) {
	// Python 3 isoformat includes +, but that makes it invalid for JS, so remove it
    //var iso = s.split('+')[0] + 'Z'; // the Z indicates UTC
	var d  = new Date(s);
	return d.toLocaleString('en-US', dt_options);
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
	// prevent multiple attempts
	if (form.getAttribute('disabled')) {
		return;
	}
	form.setAttribute('disabled', 'disabled');

    var form_data = utils.getFormData(form);

    utils.ajax('POST', form.action + '?app=1', form_data, function(data) {
        if (data.errors) {
			callback(data.errors, {});
        }
		else {
			callback({}, data);
		}

		form.removeAttribute('disabled');
    });
};

export default utils;
