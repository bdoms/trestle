import App from './app.svelte';
import Home from './home';
import User from './user';
import Auths from './auths';
import Email from './email';
import Password from './password';

// this only exists as a separate element on app pages
trestle.XSRF =  document.getElementById('xsrf').value;

const routes = {
	'/svelte/home': Home,
	'/svelte/user': User,
	'/svelte/user/auths': Auths,
	'/svelte/user/email': Email,
	'/svelte/user/password': Password
};

const app = new App({
	target: document.getElementById('app'),
	props: {
		routes: routes
	}
});

export default app;
