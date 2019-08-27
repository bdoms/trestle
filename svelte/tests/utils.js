import test from 'ava';
import utils from '../utils';

test('joinParams', t => {
    var params = {'foo': 'bar', 'truthy': true, 'falsy': false, 'with': 'encod ing'};
    var s = utils.joinParams(params);
    t.is(s, 'foo=bar&truthy=1&falsy=&with=encod%20ing');
});

test('ajax', t => {
    // mock the part that actually tries sending data
    var headers = {'X-Xsrf-Token': 'abcd1234', 'Content-Type': 'application/json'};
    XMLHttpRequest.prototype.getResponseHeader = function(key) {
        return headers[key];
    };

    var send = function(data) {
        Object.defineProperty(this, 'readyState', {
            writable: true
        });

        Object.defineProperty(this, 'responseText', {
            writable: true
        });

        this.responseHeaders = headers;
        this.readyState = 4;

        this.responseText = data; // echo back what's put in
        this.onreadystatechange();
    };

    XMLHttpRequest.prototype.send = function(data) {
        Object.defineProperty(this, 'status', {
            writable: true
        });

        this.status = 200;

        send.call(this, data);
    };

    var called_with = {};
    var callback = function(data) {
        called_with = data;
    }

    var called_error = {};
    var error_callback = function(status, data) {
        called_error = data;
    }

    // test JSON version
    var data = {'foo': 'bar'};
    var s = JSON.stringify(data);
    utils.ajax('POST', 'localhost', s, callback, error_callback);
    t.deepEqual(data, called_with);
    t.deepEqual({}, called_error);

    // test FormData version
    headers = {'Content-Type': ''};
    var form_data = new FormData();
    form_data.append('foo', 'bar');
    utils.ajax('POST', 'localhost', form_data, callback, error_callback);
    t.is('bar', called_with.get('foo'));
    t.is('abcd1234', called_with.get('_xsrf'));

    // test the form encode version - we should get back what we expect, plus the XSRF token
    utils.ajax('GET', 'www.example.com', data, callback, error_callback);
    // this gets form encoded, and it's returned exactly that way to us
    t.deepEqual('foo=bar&_xsrf=abcd1234', called_with);
    t.deepEqual({}, called_error);

    // test error callback
    XMLHttpRequest.prototype.send = function(data) {
        Object.defineProperty(this, 'status', {
            writable: true
        });

        this.status = 500;

        send.call(this, data);
    };

    called_with = {};
    utils.ajax('GET', 'www.example.com', data, callback, error_callback);
    t.deepEqual({}, called_with);
    t.deepEqual('foo=bar&_xsrf=abcd1234', called_error);
});

test('toggleForm', t => {
    var form = document.createElement('form');
    var input = document.createElement('input');
    form.append(input);
    var select = document.createElement('select');
    form.append(select);
    var textarea = document.createElement('textarea');
    form.append(textarea);

    utils.toggleForm(form, false);

    t.true(input.disabled);
    t.true(select.disabled);
    t.true(textarea.disabled);

    utils.toggleForm(form, true);

    t.false(input.disabled);
    t.false(select.disabled);
    t.false(textarea.disabled);
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
    var success = {};

    var callback2 = function(data) {
        success = data;
    };

    utils.ajax = function(method, url, data, callback) {
        callback({'foo': 'bar'});
    };

    utils.submitForm(form2, callback2);
    t.deepEqual(success, {'foo': 'bar'});
});

test('formatDateTime', t => {
    var s = '2000-01-01T13:00:52.961652';
    var result = utils.formatDateTime(s);
    t.is(result, 'January 1, 2000, 1:00 PM');
});
