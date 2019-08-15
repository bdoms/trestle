import browserEnv from 'browser-env';
browserEnv(
    // which globals to mock
    ['window', 'document', 'navigator'],
    // config to pass through to jsdom
    {'url': 'http://localhost/'}
);
