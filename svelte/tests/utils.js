import test from 'ava';
import utils from '../utils';

test('ajax', t => {
    // mock the part that actually tries sending data
    var headers = {'X-Xsrf-Token': 'abcd1234', 'Content-Type': 'application/json'};
    XMLHttpRequest.prototype.getResponseHeader = function(key) {
        return headers[key];
    };

    XMLHttpRequest.prototype.send = function(data) {
        Object.defineProperty(this, 'readyState', {
            writable: true
        });

        Object.defineProperty(this, 'status', {
            writable: true
        });

        Object.defineProperty(this, 'responseText', {
            writable: true
        });

        this.responseHeaders = headers;
        this.readyState = 4;
        this.status = 200;
        this.responseText = data; // echo back what's put in
        this.onreadystatechange();
    };

    var called_with = {};
    var callback = function(data) {
        called_with = data;
    }

    // test JSON version
    var data = {'foo': 'bar'};
    var s = JSON.stringify(data);
    utils.ajax('POST', 'localhost', s, callback);
    t.deepEqual(data, called_with);

    // test that we get back what we expect, plus the XSRF token
    headers = {'Content-Type': ''};
    utils.ajax('GET', 'www.example.com', data, callback);
    // this gets form encoded, and it's returned exactly that way to us
    t.deepEqual('foo=bar&_xsrf=abcd1234', called_with);
});

test('formatDateTime', t => {
    var s = '2000-01-01T13:00:52.961652';
    var result = utils.formatDateTime(s);
    t.is(result, 'January 1, 2000, 1:00 PM');
});

test('getFormData', t => {
    var form = document.createElement('form');
    var input = document.createElement('input');
    input.name = 'foo';
    input.value = 'bar';
    form.append(input);

    var form_data = utils.getFormData(form);
    t.deepEqual(form_data, {'foo': 'bar'});
});

test('submitForm', t => {
    // test that the form is not submitted multiple times at once
    // this is true because the callback to undo the form lock is never called in this situation
    var form = document.createElement('form');
    var called = 0;

    // mock ajax
    utils.ajax = function(method, url, data, callback) {
        called += 1;
    };

    utils.submitForm(form);
    t.is(called, 1);

    utils.submitForm(form);
    t.is(called, 1);

    // test that the callback gets called with errors
    var form2 = document.createElement('form');
    var errors = {};
    var success = {};

    var callback2 = function(error_data, success_data) {
        errors = error_data;
        success = success_data;
    };

    utils.ajax = function(method, url, data, callback) {
        callback({'errors': {'foo': 'bar'}});
    };

    utils.submitForm(form2, callback2);
    t.deepEqual(errors, {'foo': 'bar'});
    t.deepEqual(success, {});

    // test that the callback gets called for success
    utils.ajax = function(method, url, data, callback) {
        callback({'foo': 'bar'});
    };

    utils.submitForm(form2, callback2);
    t.deepEqual(errors, {});
    t.deepEqual(success, {'foo': 'bar'});
});
