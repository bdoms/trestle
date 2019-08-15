import test from 'ava';
import utils from '../utils';
import trestle from '../../static/j/main.js';

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
    trestle.ajax = function(method, url, data, callback) {
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

    trestle.ajax = function(method, url, data, callback) {
        callback({'errors': {'foo': 'bar'}});
    };

    utils.submitForm(form2, callback2);
    t.deepEqual(errors, {'foo': 'bar'});
    t.deepEqual(success, {});

    // test that the callback gets called for success
    trestle.ajax = function(method, url, data, callback) {
        callback({'foo': 'bar'});
    };

    utils.submitForm(form2, callback2);
    t.deepEqual(errors, {});
    t.deepEqual(success, {'foo': 'bar'});
});
