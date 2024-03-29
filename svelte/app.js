import App from './app.svelte';
import Home from './home';
import Account from './account';
import Auths from './auths';
import Email from './email';
import Password from './password';

import utils from './utils';

// this should come as early as possible
window.onerror = function(error, script, line, char) {
    // don't report errors from extensions
    if (script && script.indexOf('chrome-extension') > -1) {
        console.warn('Extension Error');
        return;
    }

    // don't report errors from with external scripts (ads, iframes, etc.)
    if (script === '' && (line === 0 || line === undefined) && (char === 0 || char === undefined)) {
        console.warn('Unknown Script Error');
        return;
    }

    var error_data = {'error': error, 'script': script, 'location': line + ':' + char, 'URL': document.location.href};
    utils.ajax('POST', '/logerror', {'javascript': JSON.stringify(error_data)});
};

// this is needed because Chrome does not trigger onerror from within Promises, and svelte uses them sometimes
// see https://github.com/sveltejs/svelte/issues/1096
window.onunhandledrejection = function(error) {
    // in theory the filename and linenumber are present on errors, but in practice in Chrome they didn't exist
    window.onerror.call(this, error.reason.message, error.reason.stack, error.reason.fileName, error.reason.lineNumber);
};

const routes = {
	'/svelte/home': Home,
	'/svelte/account': Account,
	'/svelte/account/auths': Auths,
	'/svelte/account/email': Email,
	'/svelte/account/password': Password
};

const app = new App({
	target: document.getElementById('app'),
	props: {
		routes: routes
	}
});

export default app;
