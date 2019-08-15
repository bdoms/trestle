// TODO: enable this for tests
// FUTURE: move anything we use from main to here so we don't have to do this
// import trestle from '../static/j/main.js';

const utils = {};

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

    trestle.ajax('POST', form.action + '?app=1', form_data, function(data) {
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
