var trestle = trestle || {};

// this only exists as a separate element on app pages
trestle.XSRF =  document.getElementById('xsrf').value;

(function() {
var self = this;

Vue.config.errorHandler = function(error, vm, info) {
    var error_data = {'error': error.toString(), 'vm': vm, 'info': info};
    trestle.ajax('POST', '/logerror', {'javascript': JSON.stringify(error_data)});
};

// utils
self.replaceTitle = function(to, from, next) {
    next(function(vm) {
        var title;
        if (vm.title) {
            title = vm.title;
        }
        else {
            title = vm.$options.name;
        }
        title += ' | Site Name';
        document.title = title;
        var url = document.location.pathname + document.location.search;
        window.history.replaceState(window.history.state, title, url);
    });
};

self.getFormData = function(form) {
    var data = {};
    var form_data = new FormData(form);
    form_data.forEach(function(value, key) {
        data[key] = value;
    });
    return data;
};

self.submitForm = function(e, callback) {
    var vm = this;

    if (vm.lock) {
        return;
    }

    vm.lock = true;
    var form = e.target;
    var form_data = self.getFormData(form);

    trestle.ajax('POST', form.action + '?app=1', form_data, function(data) {
        if (data.errors) {
            vm.errors = data.errors;
            vm.lock = false;
            return;
        }

        for (var key in data) {
            if (data.hasOwnProperty(key) && vm.hasOwnProperty(key)) {
                vm[key] = data[key];
            }
        }
        vm.lock = false;
    });
};

// components
self.HomeComponent = {
    name: 'Home',
    template: '#home-template',
    beforeRouteEnter: self.replaceTitle,
    props: ['current_user']
};

self.UserComponent = {
    name: 'User',
    template: '#user-template',
    beforeRouteEnter: self.replaceTitle,
    data: function() {return {
        title: 'Account Settings'
    };}
};

self.AuthsComponent = {
    name: 'Auths',
    template: '#auths-template',
    beforeRouteEnter: self.replaceTitle,
    data: function() {return {
        auths: [],
        current_auth_id: '',
        title: 'Active Sessions'
    };},
    props: ['current_user'],
    methods: {
        revokeAccess: function(e, index) {
            var vm = this;
            var form = e.target;
            var form_data = self.getFormData(form);
            trestle.ajax('POST', form.action + '?app=1', form_data, function(data) {
                if (data.ok) {
                    vm.auths.splice(index, 1);
                }
            });
        }
    },
    created: function() {
        var vm = this;
        trestle.ajax('GET', '/user/auths?app=1', {}, function(data) {
            vm.auths = data.auths;
            vm.current_auth_id = data.current_auth_id;
        });
    }
};

self.EmailComponent = {
    name: 'Email',
    template: '#email-template',
    beforeRouteEnter: self.replaceTitle,
    data: function() {return {
        errors: {},
        lock: false,
        ok: false,
        title: 'Change Email'
    };},
    props: ['current_user'],
    methods: {
        changeEmail: self.submitForm
    }
};

self.PasswordComponent = {
    name: 'Password',
    template: '#password-template',
    beforeRouteEnter: self.replaceTitle,
    data: function() {return {
        errors: {},
        lock: false,
        ok: false,
        title: 'Change Password'
    };},
    props: ['current_user'],
    methods: {
        changePassword: self.submitForm
    }
};


/* init app */
self.parentProps = function() {
    var current_user = self.app ? self.app.current_user : {};
    return {
        current_user: current_user
    };
};

self.routes = [
    {path: '/vue/home', component: self.HomeComponent, props: self.parentProps},
    {path: '/vue/user', component: self.UserComponent, props: self.parentProps},
    {path: '/vue/user/auths', component: self.AuthsComponent, props: self.parentProps},
    {path: '/vue/user/email', component: self.EmailComponent, props: self.parentProps},
    {path: '/vue/user/password', component: self.PasswordComponent, props: self.parentProps}
];

self.router = new VueRouter({
    mode: 'history',
    routes: self.routes,
    scrollBehavior: function(to, from, savedPosition) {
        if (savedPosition) {
            return savedPosition;
        }
        else {
            return {x: 0, y: 0};
        }
    }
});

self.app = new Vue({
    router: self.router,
    data: function() {return {
        current_user: {},
        loading: true
    };},
    methods: {
        logOut: function(e) {
            var form = document.getElementById('logout-form');
            if (!form.getAttribute('disabled')) {
                // prevent multiple attempts
                form.setAttribute('disabled', true);
                form.submit();
            }
        }
    },
    mounted: function() {
        var vm = this;
        trestle.ajax('POST', '/home', {}, function(data) {
            vm.current_user = data.user;
            vm.loading = false;
        });
    }
}).$mount('#app');

})();
